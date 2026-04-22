from .base import ProcessingError


class ImageProcessingError(ProcessingError):
    """Image processing specific errors"""
    pass


class VideoProcessingError(ProcessingError):
    """Video processing specific errors"""
    pass


class FileFormatError(ProcessingError):
    """Unsupported file format errors"""
    pass


class FileSizeError(ProcessingError):
    """File size limit exceeded errors"""
    pass


class ProcessingTimeoutError(ProcessingError):
    """Processing timeout errors"""
    pass


class MemoryError(ProcessingError):
    """Memory allocation errors during processing"""
    pass


class OpenCVError(ProcessingError):
    """OpenCV operation errors"""
    pass