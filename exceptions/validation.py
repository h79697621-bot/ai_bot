from .base import ProcessingError


class ValidationError(ProcessingError):
    """Input validation errors"""
    pass


class GridSizeError(ValidationError):
    """Invalid grid size errors"""
    pass


class AdaptationMethodError(ValidationError):
    """Invalid adaptation method errors"""
    pass


class FileTypeError(ValidationError):
    """Invalid file type errors"""
    pass


class ParameterError(ValidationError):
    """Invalid parameter errors"""
    pass
