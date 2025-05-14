import json
import re
from typing import Dict, List, Optional, Tuple

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

# ---- 拼音处理工具 ----
def convert_tone_markers(pinyin: str) -> str:
    """将带声调符号的拼音转换为数字表示（yǐ → yi3）"""
    tone_map = [
        ('ā', 'a1'), ('á', 'a2'), ('ǎ', 'a3'), ('à', 'a4'),
        ('ē', 'e1'), ('é', 'e2'), ('ě', 'e3'), ('è', 'e4'),
        ('ī', 'i1'), ('í', 'i2'), ('ǐ', 'i3'), ('ì', 'i4'),
        ('ō', 'o1'), ('ó', 'o2'), ('ǒ', 'o3'), ('ò', 'o4'),
        ('ū', 'u1'), ('ú', 'u2'), ('ǔ', 'u3'), ('ù', 'u4'),
        ('ǖ', 'v1'), ('ǘ', 'v2'), ('ǚ', 'v3'), ('ǜ', 'v4'),
        ('ü', 'v')
    ]
    for marker, replacement in tone_map:
        pinyin = pinyin.replace(marker, replacement)
    return pinyin

def split_pinyin(pinyin_str: str) -> List[str]:
    """拆分拼音字符串（处理带逗号情况）"""
    return [p.strip() for p in re.split(r'[，\s]', pinyin_str) if p.strip()]

tone_mapping = {
    '1': '̄',  # 第一声 (ā)
    '2': '́',  # 第二声 (á)
    '3': '̌',  # 第三声 (ǎ)
    '4': '̀',  # 第四声 (à)
    '5': '',   # 轻声 (a)
}

def convert_tone(match):
    pinyin_with_tone = match.group(1)  # 获取方括号内的内容，如 "ni3 hao3"
    pinyins = pinyin_with_tone.split()  # 拆分成 ["ni3", "hao3"]
    
    converted_pinyins = []
    for pinyin in pinyins:
        if pinyin[-1].isdigit():
            tone = pinyin[-1]
            base = pinyin[:-1]
            tone_mark = tone_mapping.get(tone, '')
            
            vowels = 'aeiouü'
            for i, char in enumerate(base):
                if char in vowels:
                    converted = base[:i] + char + tone_mark + base[i+1:]
                    converted_pinyins.append(converted)
                    break
            else:
                converted_pinyins.append(base + tone_mark)
        else:
            converted_pinyins.append(pinyin)
    
    return '[' + ' '.join(converted_pinyins) + ']'

# ---- 拼音转换工具 ----
def convert_numbered_pinyin(match: re.Match) -> str:
    """将数字声调拼音转换为带符号的拼音（luo2 → luó）"""
    tone_map = {
        'a': ['a', 'ā', 'á', 'ǎ', 'à'],
        'e': ['e', 'ē', 'é', 'ě', 'è'],
        'i': ['i', 'ī', 'í', 'ǐ', 'ì'],
        'o': ['o', 'ō', 'ó', 'ǒ', 'ò'],
        'u': ['u', 'ū', 'ú', 'ǔ', 'ù'],
        'v': ['ü', 'ǖ', 'ǘ', 'ǚ', 'ǜ'],
    }
    
    pinyin = match.group(1)
    tone = int(match.group(2)) if match.group(2) else 0
    
    # 处理特殊 ü 情况
    if 'u:' in pinyin:
        pinyin = pinyin.replace('u:', 'v')
    
    # 找到需要加声调的元音
    vowel_pos = -1
    for i, c in enumerate(pinyin):
        if c in 'aeiouv':
            vowel_pos = i
            # 优先处理最后一个元音
            if c != 'i' or i == len(pinyin) - 1:
                break
    
    if vowel_pos >= 0:
        vowel = pinyin[vowel_pos]
        if vowel in tone_map and 0 <= tone <= 4:
            # 替换带声调的元音
            new_vowel = tone_map[vowel][tone]
            pinyin = pinyin[:vowel_pos] + new_vowel + pinyin[vowel_pos+1:]
    
    return f"[{pinyin}]"

def convert_translation_pinyin(translation: str) -> str:
    """转换翻译文本中的所有数字声调拼音"""
    # 匹配 [拼音数字] 格式
    pattern = re.compile(r'\[([a-z]+)(\d?)\]')
    # pattern = re.compile(r'$$([a-z]+\d?(?:\s+[a-z]+\d?)*)$$')
    # return pattern.sub(convert_numbered_pinyin, translation)
    return pattern.sub(convert_numbered_pinyin, translation)

# ---- CC-CEDICT 加载 ----
def parse_cc_cedict_line(line: str) -> Optional[Tuple[str, str, str, List[str]]]:
    """解析单行CC-CEDICT数据，返回(词, 拼音, [翻译列表])"""
    if line.startswith('#') or not line.strip():
        return None
    
    # 解析行格式：繁体 简体 [拼音] /翻译1/翻译2/.../
    parts = line.split(' ', 3)
    if len(parts) < 4:
        return None
        
    trad, simp, pinyin_part, trans_part = parts
    pinyin = pinyin_part[1:-1].strip()  # 去掉方括号

    # 提取所有翻译并转换其中的拼音格式
    translations = []
    for t in trans_part.split('/')[1:-1]:
        if t.strip():
            # 转换翻译中的拼音格式
            converted = convert_translation_pinyin(t.strip())
            translations.append(converted)
    
    # # 提取所有翻译（跳过第一个和最后一个空字符串）
    # translations = [t.strip() for t in trans_part.split('/')[1:-1] if t.strip()]

    trs = ''
    for tr in translations:
        trs += tr + '\n'
    
    return (trad, simp, pinyin, trs)

def load_cc_cedict(cedict_path: str) -> Dict[Tuple[str, str], List[str]]:
    """
    加载CC-CEDICT词典
    返回：{(word, pinyin): [translation1, translation2]} 的字典
    """
    trans_dict = {}
    with open(cedict_path, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = parse_cc_cedict_line(line)
            if not parsed:
                continue
                
            trad, simp, pinyin, translations = parsed
            
            # 为简体和繁体分别建立条目
            for word in [trad, simp]:
                if word:  # 确保词不为空
                    key = (word, pinyin)
                    trans_dict[key] = translations
                    
                    # 同时建立不包含声调的索引（备用匹配）
                    key_no_tone = (word, re.sub(r'\d', '', pinyin))
                    if key_no_tone not in trans_dict:
                        trans_dict[key_no_tone] = translations
    return trans_dict

# ---- 数据处理核心 ----
def get_translation(word: str, pinyin: str, trans_dict: Dict) -> str:
    """获取最佳匹配的翻译（精确到声调）"""
    # 标准化拼音格式
    pinyin_numeric = convert_tone_markers(pinyin)  # yǐ → yi3
    pinyin_clean = re.sub(r'\d', '', pinyin_numeric)  # yi3 → yi
    
    # 优先级匹配
    for test_pinyin in [pinyin_numeric, pinyin_clean]:
        key = (word, test_pinyin)
        if key in trans_dict:
            return trans_dict[key]
    return ""

# 2. 修改现有处理函数，添加翻译
def process_character(char_data: Dict, detail_data: Dict, trans_dict: Dict) -> Dict:
    """处理单个汉字数据"""
    result = {
        "word": char_data.get("char", ""),
        "lemma": char_data.get("traditional", ""),
        "phonetic": "",
        "pinyin": [],
        "meaning": []
    }
    
    # 处理拼音（保留原始格式）
    result["pinyin"] = [
        py for py in char_data.get("pinyin", [])
        if isinstance(py, str)
    ]
    
    # 处理每个读音的解释
    for pron in detail_data.get("pronunciations", []):
        if "pinyin" not in pron:
            continue
            
        # 获取精确匹配的翻译
        current_pinyin = pron["pinyin"]
        translation = get_translation(
            word=char_data.get("char", ""),
            pinyin=current_pinyin,
            trans_dict=trans_dict
        )
        
        # 合并同音不同义的解释
        explanations = [
            exp["content"] for exp in pron.get("explanations", [])
            if "content" in exp and exp["content"]
        ]
        
        # 添加到结果
        result["meaning"].append({
            "pinyin": len(result["meaning"]),
            "original": "\n".join(explanations),
            "translation": translation
        })
    
    return result

def process_word(word_data: Dict, translation_dict: Dict) -> Optional[Dict]:
    """处理词语数据，添加翻译"""
    if "word" not in word_data or "pinyin" not in word_data:
        return None
    
    # 获取翻译
    translation = translation_dict.get(word_data["word"], "")
    
    # 拆分拼音
    pinyin_segments = (
        word_data["pinyin"] if isinstance(word_data["pinyin"], list)
        else word_data["pinyin"].split()
    )
    
    return {
        "word": word_data["word"],
        "lemma": "",
        "phonetic": "",
        "pinyin": [re.sub(r'[\d\s]', '', py) for py in pinyin_segments],
        "meaning": [{
            "pinyin": 0,
            "original": word_data.get("explanation", "") or 
                       "; ".join(exp["content"] for exp in word_data.get("explanations", []) 
                       if "content" in exp),
            "translation": translation
        }]
    }

# 3. 主转换函数
def convert_data_with_translation(
    char_base_path: str,
    char_detail_path: str,
    word_path: str,
    idiom_path: str,
    cedict_path: str,
    output_path: str
):
    """带翻译的主转换函数"""
    print("加载CC-CEDICT翻译数据...")
    translation_dict = load_cc_cedict(cedict_path)
    
    print("加载词典数据...")
    char_base = load_json_lines(char_base_path)
    char_detail = load_json_lines(char_detail_path)
    word_data = load_json_lines(word_path)
    idiom_data = load_json_lines(idiom_path)
    
    # 创建汉字映射表
    char_detail_map = {item["char"]: item for item in char_detail if "char" in item}
    
    print("处理数据并添加翻译...")
    converted_data = []
    
    # 处理汉字
    for char in char_base:
        detail = char_detail_map.get(char.get("char", ""), {})
        converted_data.append(process_character(char, detail, translation_dict))
    
    # 处理词语
    for word in word_data:
        processed = process_word(word, translation_dict)
        if processed:
            converted_data.append(processed)
    
    # 处理成语（使用词语处理函数）
    for idiom in idiom_data:
        processed = process_word(idiom, translation_dict)
        if processed:
            converted_data.append(processed)
    
    print("保存结果...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"转换完成！共处理 {len(converted_data)} 条数据")

if __name__ == "__main__":
    convert_data_with_translation(
        char_base_path="character/char_base.json",
        char_detail_path="character/char_detail.json",
        word_path="word/word.json",
        idiom_path="idiom/idiom.json",
        cedict_path="cedict_ts.u8",  # CC-CEDICT文件
        output_path="dictionary_with_translation.json"
    )