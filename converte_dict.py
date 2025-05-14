import json
import re
from typing import Dict, List, Union, Optional

# 常量定义
PINYIN_PATTERN = re.compile(r'^[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+$')

def validate_pinyin(pinyin: str) -> bool:
    """验证拼音格式（带声调符号）"""
    return bool(PINYIN_PATTERN.match(pinyin))

def clean_json_line(line: str) -> Optional[Dict]:
    """安全解析单行JSON数据"""
    line = line.strip()
    if not line:
        return None
    
    # 处理行尾逗号
    if line.endswith(','):
        line = line[:-1]
    
    # 尝试解析
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        try:
            # 二次尝试：处理单引号
            line = line.replace("'", '"')
            return json.loads(line)
        except:
            return None

def load_json_lines(file_path: str) -> List[Dict]:
    """加载JSON Lines文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = clean_json_line(line)
            if parsed:
                data.append(parsed)
    return data

def process_character(char_data: Dict, detail_data: Dict) -> Dict:
    """
    处理单个汉字数据
    返回格式：
    {
        "word": "字",
        "lemma": "繁体",
        "phonetic": "",
        "pinyin": ["zhong"],
        "meaning": [
            {
                "pinyin": 0,  # 拼音索引
                "original": "解释1\n解释2",  # 同音不同义合并
                "translation": ""
            }
        ]
    }
    """
    result = {
        "word": char_data.get("char", ""),
        "lemma": char_data.get("traditional", ""),
        "phonetic": "",
        "pinyin": [],
        "meaning": []
    }
    
    # 处理拼音（保留无效拼音用于展示）
    result["pinyin"] = [
        py for py in char_data.get("pinyin", [])
        if isinstance(py, str)  # 基本过滤，不验证格式
    ]
    
    # 处理释义（合并同音不同义的解释）
    if "pronunciations" in detail_data:
        for pron in detail_data["pronunciations"]:
            if "pinyin" not in pron:
                continue
                
            try:
                pinyin_index = result["pinyin"].index(pron["pinyin"])
            except ValueError:
                # 如果拼音不在基础数据中，添加到拼音列表
                pinyin_index = len(result["pinyin"])
                result["pinyin"].append(pron["pinyin"])
            
            # 合并同音不同义的解释
            explanations = []
            for exp in pron.get("explanations", []):
                if "content" in exp and exp["content"]:
                    explanations.append(exp["content"])
            
            if explanations or True:  # 始终添加，即使解释为空
                result["meaning"].append({
                    "pinyin": pinyin_index,
                    "original": "\n".join(explanations),
                    "translation": ""
                })
    
    # 确保每个拼音至少有一个meaning条目
    for i, py in enumerate(result["pinyin"]):
        if not any(m["pinyin"] == i for m in result["meaning"]):
            result["meaning"].append({
                "pinyin": i,
                "original": "",
                "translation": ""
            })
    
    return result

def process_word(word_data: Dict) -> Optional[Dict]:
    """处理词语数据（保持原有逻辑）"""
    if "word" not in word_data or "pinyin" not in word_data:
        return None
    
    # 拆分拼音
    pinyin_segments = (
        word_data["pinyin"] if isinstance(word_data["pinyin"], list)
        else word_data["pinyin"].split()
    )
    
    # 验证长度
    if len(word_data["word"]) != len(pinyin_segments):
        return None
    
    # 保留原始拼音（不验证）
    valid_pinyins = [re.sub(r'[\d\s]', '', py) for py in pinyin_segments]
    
    # 获取解释（合并多解释）
    explanation = word_data.get("explanation", "")
    if not explanation and "explanations" in word_data:
        explanations = []
        for exp in word_data["explanations"]:
            if "content" in exp and exp["content"]:
                explanations.append(exp["content"])
        explanation = "\n".join(explanations)
    
    return {
        "word": word_data["word"],
        "lemma": "",
        "phonetic": "",
        "pinyin": valid_pinyins,
        "meaning": [{
            "pinyin": 0,
            "original": explanation if explanation else "",
            "translation": ""
        }]
    }

def process_idiom(idiom_data: Dict) -> Optional[Dict]:
    """处理成语数据，统一移除中文逗号"""
    if "word" not in idiom_data or "pinyin" not in idiom_data:
        return None
    
    # 1. 处理成语文本（保留原始格式）
    clean_word = idiom_data["word"]  # 不再移除逗号
    
    # 2. 处理拼音（特殊处理中文逗号）
    raw_pinyin = idiom_data["pinyin"]
    
    # 方法一：优先按空格和中文逗号分割
    pinyin_segments = []
    for segment in re.split(r'[，\s]', raw_pinyin):  # 同时按中文逗号和空格分割
        segment = re.sub(r'\d', '', segment.strip())  # 移除数字声调
        if segment:
            pinyin_segments.append(segment)
    
    # 构建结果
    result = {
        "word": clean_word,
        "lemma": "",
        "phonetic": "",
        "pinyin": pinyin_segments,
        "meaning": []
    }
    
    # 合并解释来源（增强错误处理）
    explanations = []
    
    # 1. 添加基本解释
    if idiom_data.get("explanation"):
        explanations.append(idiom_data["explanation"])
    
    # 2. 添加故事（处理字符串或列表格式）
    if "story" in idiom_data:
        if isinstance(idiom_data["story"], list):
            explanations.extend(idiom_data["story"])
        elif idiom_data["story"]:
            explanations.append(idiom_data["story"])
    
    # 3. 添加例句（处理字典或字符串格式）
    if "example" in idiom_data:
        example_text = ""
        if isinstance(idiom_data["example"], dict):
            example_text = idiom_data["example"].get("text", "")
            if "book" in idiom_data["example"]:
                example_text += f"（出处：{idiom_data['example']['book']}）"
        elif idiom_data["example"]:
            example_text = str(idiom_data["example"])
        
        if example_text:
            explanations.append(f"例句：{example_text}")
    
    # 4. 添加近反义词
    if idiom_data.get("similar"):
        explanations.append(f"近义词：{'、'.join(idiom_data['similar'])}")
    if idiom_data.get("opposite"):
        explanations.append(f"反义词：{'、'.join(idiom_data['opposite'])}")
    
    # 合并到结果
    if explanations:
        result["meaning"].append({
            "pinyin": 0,
            "original": "\n".join(explanations),
            "translation": ""
        })
    else:
        result["meaning"].append({
            "pinyin": 0,
            "original": "",
            "translation": ""
        })
    
    return result

def convert_data(
    char_base_path: str,
    char_detail_path: str,
    word_path: str,
    idiom_path: str,
    output_path: str,
    max_items: int = None
):
    """主转换函数"""
    print("正在加载数据...")
    char_base = load_json_lines(char_base_path)
    char_detail = load_json_lines(char_detail_path)
    word_data = load_json_lines(word_path)
    idiom_data = load_json_lines(idiom_path)
    
    # 创建汉字映射表
    char_detail_map = {}
    for item in char_detail:
        if "char" in item:
            char_detail_map[item["char"]] = item
    
    print("正在处理数据...")
    converted_data = []
    
    # 处理汉字（不再跳过任何记录）
    for char in char_base[:max_items] if max_items else char_base:
        detail = char_detail_map.get(char.get("char", ""), {})
        converted_data.append(process_character(char, detail))
    
    # 处理词语
    for word in word_data:
        processed = process_word(word)
        if processed:  # 词语仍做基本过滤
            converted_data.append(processed)
            if max_items and len(converted_data) >= max_items:
                break

    # 优先处理成语（使用专门函数）
    for idiom in idiom_data:
        processed = process_idiom(idiom)
        if processed:
            converted_data.append(processed)

    print("正在保存结果...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"转换完成！共处理 {len(converted_data)} 条数据")

if __name__ == "__main__":
    convert_data(
        char_base_path="character/char_base.json",
        char_detail_path="character/char_detail.json",
        word_path="word/word.json",
        idiom_path="idiom/idiom.json",
        output_path="converted_dictionary.json"
    )