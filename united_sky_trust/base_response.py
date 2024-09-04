from rest_framework.response import Response

class BaseResponse:
    @staticmethod
    def response(status, HTTP_STATUS, message=None, data=None):
        base_response = {
                'status': status,
                'message': message,
                'data': data,
            }
        if status == True:
            base_response['status'] = 'success'
        else:
            base_response['status'] = 'failed'
            base_response.pop('data')
        return Response(base_response, status=HTTP_STATUS)
    
    @staticmethod
    def error_response(status_code, message=None, isError=True):
         
         if message is None:
             base_response.pop('message')
             
         base_response = {
                'status': 'failed',
                'message': message,
                'isError': isError
            }
         return Response(base_response, status=status_code)
        