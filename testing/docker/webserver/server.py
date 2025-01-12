import http.server
import os


class PathTraversalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'r') as file:
                self.wfile.write(file.read().encode())
            return

        query = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(qc.split('=') for qc in query.split('&') if '=' in qc)
        file_path = params.get('path', '')

        if file_path and os.path.isfile(file_path):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            with open(file_path, 'r') as file:
                self.wfile.write(file.read().encode())
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server_address = ('', 80)
    httpd = http.server.HTTPServer(server_address,
                                   PathTraversalHTTPRequestHandler)
    print("Serving on port 8000...")
    httpd.serve_forever()
