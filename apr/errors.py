"""统一异常类型。"""


class AprError(Exception):
    """基础异常。"""


class ConfigError(AprError):
    """配置错误。"""


class ScanError(AprError):
    """扫描错误。"""


class EvidenceError(AprError):
    """证据采集错误。"""


class LLMError(AprError):
    """LLM 调用/解析错误。"""


class QuizAborted(AprError):
    """用户在实践验证问答中主动退出。"""
