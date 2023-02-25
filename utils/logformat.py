
class LogFormat:
    
    def __init__(self,
                 message : str):
        self._message = message
    
    @property
    def message(self):
        return self._message
    
    def message_with_border(self,
                            width : int = 60,
                            border_char : str = '='):
        border_len = (width - len(self.message)) // 2
        border = border_char * border_len
        result = f'{border} {self.message} {border}'
        if len(result) < width:
            result += border_char * (width - len(result))
        return result