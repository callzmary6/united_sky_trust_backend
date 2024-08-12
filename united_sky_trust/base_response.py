from rest_framework.response import Response

class BaseResponse:
    @staticmethod
    def response(status, HTTP_STATUS, message=None, data=None):
        base_response = {
                'status': status,
                'message': message,
                'data': data
            }
        if status == True:
            base_response['status'] = 'success'
        else:
            base_response['status'] = 'failed'
            base_response.pop('data')
        return Response(base_response, status=HTTP_STATUS)