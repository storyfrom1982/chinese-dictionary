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
    if not line or line.startswith(('//', '#')):  # 跳过空行和注释
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

def process_character(char_data: Dict, detail_data: Dict) -> Optional[Dict]:
    """处理单个汉字数据"""
    if "char" not in char_data:
        return None
    
    result = {
        "word": char_data["char"],
        "lemma": char_data.get("traditional", ""),
        "phonetic": "",
        "pinyin": [],
        "meaning": []
    }
    
    # 处理拼音
    for py in char_data.get("pinyin", []):
        if validate_pinyin(py):
            result["pinyin"].append(py)
    
    # 处理释义
    if "pronunciations" in detail_data:
        for pron in detail_data["pronunciations"]:
            if "pinyin" not in pron:
                continue
                
            try:
                pinyin_index = result["pinyin"].index(pron["pinyin"])
            except ValueError:
                continue
                
            for exp in pron.get("explanations", []):
                if "content" in exp:
                    result["meaning"].append({
                        "pinyin": pinyin_index,
                        "original": exp["content"],
                        "translation": ""
                    })
    
    return result if (result["pinyin"] and result["meaning"]) else None

def process_word(word_data: Dict) -> Optional[Dict]:
    """处理词语数据"""
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
    
    # 清理拼音
    valid_pinyins = []
    for py in pinyin_segments:
        py_clean = re.sub(r'[\d\s]', '', py)
        if validate_pinyin(py_clean):
            valid_pinyins.append(py_clean)
    
    if not valid_pinyins:
        return None
    
    # 获取解释
    explanation = word_data.get("explanation", "")
    if not explanation and "explanations" in word_data:
        explanations = []
        for exp in word_data["explanations"]:
            if "content" in exp:
                explanations.append(exp["content"])
        explanation = "; ".join(explanations)
    
    if not explanation:
        return None
    
    return {
        "word": word_data["word"],
        "lemma": "",
        "phonetic": "",
        "pinyin": valid_pinyins,
        "meaning": [{
            "pinyin": 0,
            "original": explanation,
            "translation": ""
        }]
    }

def convert_data(
    char_base_path: str,
    char_detail_path: str,
    word_path: str,
    idiom_path: str,
    output_path: str,
    max_items: int = None
):
    """稳定的主转换函数"""
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
    
    # 处理汉字
    for char in char_base[:max_items] if max_items else char_base:
        if "char" not in char:
            continue
            
        detail = char_detail_map.get(char["char"])
        if not detail:
            continue
            
        processed = process_character(char, detail)
        if processed:
            converted_data.append(processed)
    
    # 处理词语
    for word in word_data + idiom_data:
        processed = process_word(word)
        if processed:
            converted_data.append(processed)
            if max_items and len(converted_data) >= max_items:
                break
    
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