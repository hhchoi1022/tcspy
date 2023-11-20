
class CoordinateError(Exception):
    """ Raise CoordinateError when the input coordinate is written in undefined format

    Args:
        Exception (_type_): _description_
    """
    
    def __init__(self, message):
        self.message = message
        super().__init__(message)
        