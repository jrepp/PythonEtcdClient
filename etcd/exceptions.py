class EtcdException(Exception):
    pass

#class EtcdHttpException(EtcdException):
#    def __init__(self, message, response):
#        super(EtcdHttpException, self).__init__(message)
#        self.__code = response.status_code
#
#    @property
#    def code(self):
#        return self.__code
#
#class EtcdHttpNotFoundException(EtcdHttpException):
#    pass
