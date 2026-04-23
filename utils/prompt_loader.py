

from utils.config_handler import prompts_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


# 先得到模板路径，然后打开
def load_system_prompt():
    try:
        system_prompt_path = get_abs_path(prompts_conf['main_prompt_path'])
    except KeyError as e:
        logger.error("[主提示词模板]在yaml中没有找到main_prompt_path配置项")
        raise e

    try:
        return open(system_prompt_path, 'r', encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[主提示词模板]解析提示词时出错，{str(e)}")
        raise e


def load_rag_prompt():
    try:
        rag_prompt_path = get_abs_path(prompts_conf['rag_summarize_prompt_path'])
    except KeyError as e:
        logger.error("[rag提示词模板]在yaml中没有找到rag_summarize_prompt_path配置项")
        raise e

    try:
        return open(rag_prompt_path, 'r', encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[rag提示词模板]解析提示词时出错，{str(e)}")
        raise e

def load_report_prompt():
    try:
        report_prompt_path = get_abs_path(prompts_conf['report_prompt_path'])
    except KeyError as e:
        logger.error("[report提示词模板]在yaml中没有找到report_prompt_path配置项")
        raise e

    try:
        return open(report_prompt_path, 'r', encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[report提示词模板]解析提示词时出错，{str(e)}")
        raise e

if __name__ == '__main__':
    res = load_rag_prompt()
    print(res)