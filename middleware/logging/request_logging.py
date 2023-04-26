from quart import Quart, request, g
from time import time

def use_request_logging(app: Quart):
    
    @app.before_request
    def log_request_start():
        g.request_start_time = time()
        # app.logger.debug(f'{request.method}:{request.url} from {request.remote_addr} received')

    @app.after_request
    def log_request_end(response):

        request_time = time() - g.request_start_time

        app.logger.info(f'{request.method}:{request.url} from {request.remote_addr} complete. Took {int(request_time*1000)}ms. {response}')

        return response