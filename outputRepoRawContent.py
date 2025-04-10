#!/usr/bin/env python3
"""
GitHub 仓库内容获取与整理脚本

功能：
1. 读取配置文件中的 GitHub 仓库 URL
2. 克隆仓库到本地
3. 输出文件目录结构
4. 提取所有代码文件(包括 README)，每个文件前添加路径信息
5. 生成处理日志

使用方法: python outputRepoRawContent.py [配置文件路径]
"""

import os
import sys
import time
import logging
import tempfile
import shutil
import subprocess
import stat
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# 删除 GitPython 依赖，完全使用命令行工具，减少出错可能
# 配置日志
def setup_logging(log_dir):
    """设置日志配置"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

def get_repo_name_from_url(repo_url):
    """从 URL 中提取仓库名称"""
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        return None
    
    repo_name = path_parts[1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    return repo_name

# 用于解决Windows上的权限问题，确保可以删除文件
def remove_readonly_and_hidden(func, path, _):
    """修改文件权限，使其可以被删除"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_repository(repo_url, target_dir):
    """克隆仓库到指定目录，完全使用simple_download.py中验证成功的方法"""
    logging.info(f"正在克隆仓库: {repo_url}")
    print(f"开始下载仓库: {repo_url}")
    
    # 确保目标目录存在但为空
    if os.path.exists(target_dir):
        try:
            # 使用自定义错误处理函数删除只读文件
            shutil.rmtree(target_dir, onerror=remove_readonly_and_hidden)
        except Exception as e:
            logging.warning(f"清理目标目录失败: {e}")
            
    os.makedirs(target_dir, exist_ok=True)
    print(f"将下载到: {target_dir}")
    
    # 设置代理环境变量
    proxy = "http://127.0.0.1:7890"
    env = os.environ.copy()
    env['HTTP_PROXY'] = proxy
    env['HTTPS_PROXY'] = proxy
    logging.info(f"使用代理: {proxy}")
    print(f"使用代理: {proxy}")
    
    # 方法1: 尝试直接使用命令行Git
    logging.info("方法1: 尝试使用命令行Git...")
    print("\n方法1: 尝试使用命令行Git...")
    git_paths = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        "git"  # 系统PATH中的git
    ]
    
    for git_path in git_paths:
        try:
            # 添加代理配置到Git命令
            proxy_config = f' -c http.proxy="{proxy}" -c https.proxy="{proxy}"'
            cmd = f'"{git_path}"{proxy_config} clone --depth=1 {repo_url} "{target_dir}"'
            logging.info(f"执行命令: {cmd}")
            print(f"执行命令: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300, env=env)
            if result.returncode == 0:
                logging.info("下载成功!")
                print("下载成功!")
                return True
            else:
                logging.warning(f"命令失败: {result.stderr}")
                print(f"命令失败: {result.stderr}")
        except Exception as e:
            logging.warning(f"尝试{git_path}失败: {str(e)}")
            print(f"尝试失败: {str(e)}")
    
    # 方法2: 尝试使用WSL Git (避免路径转换问题)
    logging.info("方法2: 尝试使用WSL...")
    print("\n方法2: 尝试使用WSL...")
    try:
        # 创建一个临时目录
        timestamp = int(time.time())
        wsl_tmp_dir = f"/tmp/gitclone_{timestamp}"
        
        # 构建完整的bash命令序列 - 添加代理配置
        proxy_config = f"export http_proxy={proxy} && export https_proxy={proxy} && "
        bash_cmd = f"""{proxy_config}mkdir -p {wsl_tmp_dir} && 
cd {wsl_tmp_dir} && 
git config --global http.sslVerify false && 
{proxy_config}git clone --depth=1 {repo_url} repo && 
mkdir -p "{target_dir}" && 
cp -r repo/* "{target_dir}/" && 
chmod -R 755 "{target_dir}" &&
rm -rf {wsl_tmp_dir}"""
        
        # 替换Windows路径为WSL路径
        wsl_path = target_dir.replace('\\', '/')
        if wsl_path[1] == ':':  # 检测Windows路径
            drive = wsl_path[0].lower()
            wsl_path = f"/mnt/{drive}/{wsl_path[3:]}"
        
        # 将Windows路径替换为WSL路径
        bash_cmd = bash_cmd.replace(target_dir, wsl_path)
        
        wsl_cmd = f'wsl bash -c "{bash_cmd}"'
        logging.info(f"执行WSL命令: {wsl_cmd}")
        print(f"执行WSL命令...\n{wsl_cmd}")
        
        result = subprocess.run(wsl_cmd, shell=True, capture_output=True, text=True, timeout=600, env=env)
        if result.returncode == 0:
            logging.info("使用WSL下载成功!")
            print("使用WSL下载成功!")
            return True
        else:
            logging.warning(f"WSL命令失败: {result.stderr}")
            print(f"WSL命令失败: {result.stderr}")
    except Exception as e:
        logging.warning(f"WSL尝试失败: {str(e)}")
        print(f"WSL尝试失败: {str(e)}")
    
    logging.error("所有方法都失败了")
    print("\n所有方法都失败了")
    return False

def generate_file_structure(repo_dir, output_file):
    """生成文件目录结构并写入文件"""
    logging.info(f"正在生成文件目录结构: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"仓库文件目录结构\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for root, dirs, files in os.walk(repo_dir):
            # 转换为相对路径
            rel_path = os.path.relpath(root, repo_dir)
            if rel_path == '.':
                level = 0
            else:
                level = rel_path.count(os.sep) + 1
            
            indent = '  ' * level
            if rel_path != '.':
                f.write(f"{indent}{os.path.basename(root)}/\n")
            
            sub_indent = '  ' * (level + 1)
            for file in sorted(files):
                f.write(f"{sub_indent}{file}\n")

def extract_code_files(repo_dir, output_dir, max_size_mb=15):
    """提取所有代码文件，每个文件前添加路径信息，确保输出文件有普通权限"""
    logging.info(f"开始提取代码文件到: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    
    skipped_files = []
    processed_files = []
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # 定义二进制文件扩展名列表，这些文件将被跳过
    binary_extensions = {
        # 图片文件
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.svg', '.webp',
        # 音视频文件
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv', '.flv', '.ogg',
        # 文档和压缩文件
        '.pdf', '.ppt', '.pptx', '.xls', '.xlsx',
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        # 编译产物和可执行文件
        '.exe', '.dll', '.so', '.dylib', '.class', '.pyc', '.pyo',
        '.obj', '.o', '.a', '.lib', '.jar', '.whl', '.egg',
        # 数据库和二进制数据文件
        '.db', '.sqlite', '.sqlite3', '.mdb', '.dat', '.bin',
        # 其他常见二进制格式
        '.ttf', '.otf', '.woff', '.woff2', '.eot'
    }
    
    # Git相关文件，这些文件对内容分析没有太大帮助
    git_related_files = [
        '.gitignore', 
        '.gitattributes', 
        '.gitmodules',
        '.github_ISSUE_TEMPLATE_bug_report.md',
        'CODEOWNERS',
        '.mailmap'
    ]
    
    # 统计数据
    skipped_by_extension = 0
    skipped_by_size = 0
    skipped_by_decode_error = 0
    skipped_git_files = 0
    
    for root, _, files in os.walk(repo_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            # 跳过 .git 目录中的文件
            if '.git' in file_path.split(os.sep):
                continue
                
            rel_path = os.path.relpath(file_path, repo_dir)
            
            # 跳过Git相关文件
            if file in git_related_files or any(rel_path.endswith(git_file) for git_file in git_related_files):
                logging.info(f"跳过Git相关文件: {rel_path}")
                skipped_files.append((rel_path, 0))
                skipped_git_files += 1
                continue
            
            # 跳过.github目录中的文件
            if '.github' in file_path.split(os.sep):
                logging.info(f"跳过GitHub配置文件: {rel_path}")
                skipped_files.append((rel_path, 0))
                skipped_git_files += 1
                continue
            
            # 基于扩展名预筛选
            _, file_ext = os.path.splitext(file.lower())
            if file_ext in binary_extensions:
                logging.info(f"基于扩展名跳过二进制文件: {rel_path}")
                skipped_files.append((rel_path, 0))  # 大小设为0表示未检查
                skipped_by_extension += 1
                continue
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size > max_size_bytes:
                    logging.warning(f"文件过大，已跳过: {rel_path} ({file_size / 1024 / 1024:.2f} MB)")
                    skipped_files.append((rel_path, file_size))
                    skipped_by_size += 1
                    continue
            except Exception as e:
                logging.warning(f"获取文件大小失败: {rel_path}, {str(e)}")
                skipped_files.append((rel_path, 0))
                continue
            
            # 确定输出文件路径
            safe_name = rel_path.replace('/', '_').replace('\\', '_')
            output_file = os.path.join(output_dir, safe_name)
            
            try:
                with open(file_path, 'rb') as src_file:
                    content = src_file.read()
                    
                    try:
                        # 尝试以 utf-8 解码
                        content_str = content.decode('utf-8')
                        
                        with open(output_file, 'w', encoding='utf-8') as dest_file:
                            # 在文件开头添加路径信息
                            dest_file.write(f"// 文件路径: {rel_path}\n")
                            dest_file.write(f"// 提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            dest_file.write(content_str)
                            
                        # 确保输出文件有正常权限
                        os.chmod(output_file, 0o644)  # rw-r--r--
                        processed_files.append(rel_path)
                        
                    except UnicodeDecodeError:
                        # 跳过二进制文件
                        logging.info(f"解码失败，跳过二进制文件: {rel_path}")
                        skipped_files.append((rel_path, file_size))
                        skipped_by_decode_error += 1
                        
            except Exception as e:
                logging.error(f"处理文件出错 {rel_path}: {str(e)}")
    
    # 记录统计信息
    logging.info(f"处理完成 - 已处理文件: {len(processed_files)}个")
    logging.info(f"跳过文件统计 - Git相关: {skipped_git_files}个, 扩展名筛选: {skipped_by_extension}个, 文件过大: {skipped_by_size}个, 解码失败: {skipped_by_decode_error}个")
    
    return processed_files, skipped_files, skipped_git_files

def process_repository(repo_url, output_base_dir):
    """处理单个仓库的主函数"""
    start_time = datetime.now()
    logging.info(f"开始处理仓库: {repo_url}")
    print(f"正在处理仓库: {repo_url}")
    
    # 创建临时目录用于克隆仓库
    temp_dir = tempfile.mkdtemp()
    logging.info(f"创建临时目录: {temp_dir}")
    print(f"创建临时目录: {temp_dir}")
    
    try:
        # 获取仓库名
        repo_name = get_repo_name_from_url(repo_url)
        if not repo_name:
            logging.error(f"无法从URL解析仓库名: {repo_url}")
            print(f"错误: 无法从URL解析仓库名: {repo_url}")
            return
            
        # 创建输出目录
        repo_output_dir = os.path.join(output_base_dir, repo_name)
        os.makedirs(repo_output_dir, exist_ok=True)
        logging.info(f"创建输出目录: {repo_output_dir}")
        
        # 克隆仓库，使用直接调用命令行的方法（与simple_download.py相同）
        logging.info(f"开始克隆仓库到临时目录: {temp_dir}")
        clone_success = clone_repository(repo_url, temp_dir)
        
        if not clone_success:
            # 创建失败记录文件
            failure_file = os.path.join(repo_output_dir, f"{repo_name}_clone_failed.txt")
            with open(failure_file, 'w', encoding='utf-8') as f:
                f.write(f"克隆失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"仓库URL: {repo_url}\n\n")
                f.write(f"错误信息: 所有克隆方法都失败\n")
            logging.info(f"已创建失败记录文件: {failure_file}")
            print(f"克隆失败，详情请查看日志。")
            return
            
        # 检查克隆的仓库内容
        files_count = 0
        for root, dirs, files in os.walk(temp_dir):
            files_count += len(files)
        logging.info(f"克隆成功，共获取到 {files_count} 个文件")
        print(f"克隆成功，共获取到 {files_count} 个文件")
        
        # 修改临时目录内所有文件的权限，确保可以正常删除
        for root, dirs, files in os.walk(temp_dir):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o755)  # rwxr-xr-x
                except:
                    pass
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), 0o644)  # rw-r--r--
                except:
                    pass
        
        # 生成文件目录结构
        structure_file = os.path.join(repo_output_dir, f"{repo_name}_file_structure.txt")
        logging.info(f"生成文件结构: {structure_file}")
        generate_file_structure(temp_dir, structure_file)
        
        # 创建空的 general 总结文件
        general_file = os.path.join(repo_output_dir, f"{repo_name}_general_summary.txt")
        with open(general_file, 'w', encoding='utf-8') as f:
            pass
        
        # 提取代码文件，默认最大文件大小限制为15MB
        max_size_mb = 15
        code_output_dir = os.path.join(repo_output_dir, "code_files")
        logging.info(f"提取代码文件到: {code_output_dir}")
        processed_files, skipped_files, skipped_git_files = extract_code_files(temp_dir, code_output_dir, max_size_mb)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 记录处理结果
        summary_file = os.path.join(repo_output_dir, f"{repo_name}_processing_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"仓库处理摘要: {repo_name}\n")
            f.write(f"源 URL: {repo_url}\n")
            f.write(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"处理时长: {duration:.2f} 秒\n\n")
            
            f.write(f"已处理文件数: {len(processed_files)}\n")
            f.write(f"跳过的文件总数: {len(skipped_files)}\n\n")
            
            # 统计跳过文件的原因
            skipped_by_extension = sum(1 for _, size in skipped_files if size == 0)
            skipped_by_size = sum(1 for _, size in skipped_files if size > max_size_mb * 1024 * 1024)
            skipped_others = len(skipped_files) - skipped_by_extension - skipped_by_size - skipped_git_files
            
            f.write(f"跳过文件详情:\n")
            f.write(f"  Git相关文件: {skipped_git_files}个\n")
            f.write(f"  基于文件扩展名: {skipped_by_extension}个\n")
            f.write(f"  文件过大 (>{max_size_mb}MB): {skipped_by_size}个\n")
            f.write(f"  解码错误或其他原因: {skipped_others}个\n\n")
            
            # 列出跳过的大文件
            large_files = [(path, size) for path, size in skipped_files if size > max_size_mb * 1024 * 1024]
            if large_files:
                f.write(f"跳过的大文件 (>{max_size_mb}MB):\n")
                for file_path, size in large_files:
                    f.write(f"  {file_path}: {size / 1024 / 1024:.2f} MB\n")
        
        # 确保记录文件有正常权限
        os.chmod(summary_file, 0o644)
        os.chmod(general_file, 0o644)
        os.chmod(structure_file, 0o644)
        
        logging.info(f"仓库处理完成: {repo_name}")
        logging.info(f"已处理文件数: {len(processed_files)}; 跳过的文件总数: {len(skipped_files)}")
        print(f"成功完成处理: {repo_name}, 处理了 {len(processed_files)} 个文件")
        
    except Exception as e:
        logging.error(f"处理仓库时出错: {str(e)}")
        print(f"处理仓库时出错: {str(e)}")
    
    finally:
        # 清理临时目录，使用自定义错误处理程序处理只读或系统文件
        try:
            if os.path.exists(temp_dir):
                logging.info(f"清理临时目录: {temp_dir}")
                print(f"清理临时目录: {temp_dir}")
                shutil.rmtree(temp_dir, onerror=remove_readonly_and_hidden)
        except Exception as e:
            logging.warning(f"清理临时目录失败: {str(e)}")
            print(f"清理临时目录失败: {str(e)}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(f"使用方法: {sys.argv[0]} [配置文件路径]")
        print(f"默认将使用当前目录下的 target.ini")
        config_file = "target.ini"
    else:
        config_file = sys.argv[1]
    
    # 显示系统信息
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {os.name} {sys.platform}")
    
    # 检查环境变量中是否设置了HTTP代理
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    if http_proxy or https_proxy:
        proxy = http_proxy or https_proxy
        print(f"检测到系统代理设置: {proxy}")
    
    # 设置输出目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not script_dir:  # 如果为空，使用当前目录
        script_dir = os.getcwd()
    print(f"脚本目录: {script_dir}")
    
    output_dir = os.path.join(script_dir, "repo_contents")
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")
    
    # 设置日志目录
    log_dir = os.path.join(output_dir, "logs")
    log_file = setup_logging(log_dir)
    
    logging.info(f"开始执行仓库内容提取流程")
    logging.info(f"配置文件: {config_file}")
    logging.info(f"输出目录: {output_dir}")
    
    overall_start_time = datetime.now()
    
    try:
        # 检查配置文件
        config_path = config_file
        if not os.path.isabs(config_file):
            config_path = os.path.join(script_dir, config_file)
        
        if not os.path.exists(config_path):
            alt_config_path = os.path.join(os.getcwd(), config_file)
            if os.path.exists(alt_config_path):
                config_path = alt_config_path
                logging.info(f"使用替代配置文件路径: {config_path}")
            else:
                logging.error(f"配置文件不存在: {config_path}")
                print(f"错误: 找不到配置文件，已尝试路径: {config_path} 和 {alt_config_path}")
                return
        
        logging.info(f"从配置文件读取: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        logging.info(f"从配置文件中读取到 {len(urls)} 个仓库 URL")
        for idx, url in enumerate(urls):
            logging.info(f"URL[{idx+1}]: {url}")
        
        # 处理每个仓库
        for i, repo_url in enumerate(urls, 1):
            logging.info(f"处理仓库 [{i}/{len(urls)}]: {repo_url}")
            process_repository(repo_url, output_dir)
        
        overall_end_time = datetime.now()
        overall_duration = (overall_end_time - overall_start_time).total_seconds()
        logging.info(f"所有仓库处理完成！总时长: {overall_duration:.2f} 秒")
        
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
        print(f"错误: {str(e)}")
        
    logging.info(f"日志文件位置: {log_file}")
    print(f"处理完成，日志文件: {log_file}")

if __name__ == "__main__":
    main()
