import zipfile
import os
from datetime import datetime
from io import BytesIO

from odoo import http
from odoo.http import request, content_disposition


class Binary(http.Controller):

    @http.route('/web/binary/download_github_repository', type='http', auth='user')
    def download_zip(self, **kwargs):
        repo_path = kwargs.get('repo_path', False)
        repo_name = kwargs.get('repo_name', False)
        repo_branch = kwargs.get('repo_branch', False)
        if not repo_path or not os.path.isdir(repo_path):
            return request.not_found()
        zip_filename = f"{repo_name}_{repo_branch}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.zip"
        bit_io = BytesIO()
        with zipfile.ZipFile(bit_io, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(repo_path):
                # Excluir la carpeta .git y su contenido
                if '.git' in dirs:
                    dirs.remove('.git')
                for file in files:
                    if file == '.gitignore':
                        continue
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, repo_path)
                    zip_file.write(abs_path, rel_path)
        bit_io.seek(0)
        return request.make_response(bit_io.getvalue(), headers=[
            ('Content-Type', 'application/x-zip-compressed'),
            ('Content-Disposition', content_disposition(zip_filename))
        ])
