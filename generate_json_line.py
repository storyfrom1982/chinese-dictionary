import json
import os

def json_objects_to_lines(input_json_file, output_file_prefix, max_lines_per_file=50000):
    """
    从JSON文件加载数据，将每个对象转换为一行文本写入文件，超过指定行数自动分文件
    
    参数:
        input_json_file: 输入的JSON文件路径
        output_file_prefix: 输出文件前缀（会自动添加_序号.txt）
        max_lines_per_file: 每个文件最大行数（默认为50000）
    """
    try:
        # 读取JSON文件
        with open(input_json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件 {input_json_file} 未找到")
        return
    except json.JSONDecodeError:
        print(f"错误: 文件 {input_json_file} 不是有效的JSON格式")
        return
    
    # 检查数据格式
    if not isinstance(data, (dict, list)):
        print("错误: JSON数据必须是对象或对象数组")
        return
    
    # 如果是字典，转换为列表形式
    if isinstance(data, dict):
        data = [data]
    
    # 分文件写入
    file_count = 1
    line_count = 0
    current_file = None
    
    for i, obj in enumerate(data, 1):
        # 每max_lines_per_file行创建一个新文件
        if line_count % max_lines_per_file == 0:
            if current_file is not None:
                current_file.close()
            output_file = f"{output_file_prefix}_{file_count}.json"
            current_file = open(output_file, 'w', encoding='utf-8')
            file_count += 1
            line_count = 0
        
        # 将对象转换为一行文本
        line = json.dumps(obj, ensure_ascii=False)
        current_file.write(line + '\n')
        line_count += 1
        
        # 打印进度
        if i % 1000 == 0:
            print(f"已处理 {i}/{len(data)} 条数据，当前写入文件: {output_file}")
    
    # 关闭最后一个文件
    if current_file is not None:
        current_file.close()
    
    print(f"处理完成！共处理 {len(data)} 条数据，生成 {file_count-1} 个文件")

# 示例用法
if __name__ == "__main__":
    # 使用示例（直接指定输入JSON文件和输出前缀）
    input_file = "converted_dictionary.json"  # 替换为您的JSON文件路径
    output_prefix = "chinese-words"
    
    json_objects_to_lines(input_file, output_prefix, 100000)
    
    # 如果想改为每5000条一个文件：
    # json_objects_to_lines(input_file, output_prefix, 5000)