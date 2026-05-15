import requests
from xml.etree import ElementTree
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER
)


class NextcloudClient:
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USERNAME
        self.password = NEXTCLOUD_PASSWORD
        folder = NEXTCLOUD_FOLDER
        if not folder.startswith('/'):
            folder = '/' + folder
        self.folder = folder

    def upload_file(self, file_content, filename):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.put(
                url,
                data=file_content,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/octet-stream'}
            )
            if response.status_code in [200, 201, 204]:
                return filename
            else:
                print(f"Nextcloud upload failed: HTTP {response.status_code} - {response.reason}")
                print(f"Response body: {response.text[:500]}")
                return None
        except Exception as e:
            print(f"Nextcloud upload error: {e}")
            return None

    def delete_file(self, filename):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.delete(url, auth=(self.username, self.password))
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Nextcloud delete error: {e}")
            return False

    def download_file(self, file_id_or_name):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{file_id_or_name}"
        try:
            response = requests.get(url, auth=(self.username, self.password))
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Nextcloud download error: {e}")
            return None

    def list_files(self):
        """
        Return a set of filenames (strings) present in the configured Nextcloud folder.
        """
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}"
        headers = {"Depth": "1"}
        response = requests.request(
            "PROPFIND", url, auth=(self.username, self.password), headers=headers
        )
        if response.status_code != 207:
            raise Exception(f"PROPFIND failed: {response.status_code} {response.text}")

        root = ElementTree.fromstring(response.content)
        ns = {"d": "DAV:"}
        filenames = set()
        prefix = f"/remote.php/dav/files/{self.username}{self.folder}"
        for response_elem in root.findall("d:response", ns):
            href = response_elem.find("d:href", ns).text
            if href.startswith(prefix):
                name = href[len(prefix):].strip("/")
                if name:  # ignore the folder itself
                    filenames.add(name)
        return filenames


def get_file_from_cloud(media):
    content = None
    content_type = 'video/mp4' if media.media_type == 'video' else 'image/jpeg'
    nc = NextcloudClient()

    # Try the stored nextcloud_file_id first (works for new uploads)
    if media.nextcloud_file_id:
        content = nc.download_file(media.nextcloud_file_id)

    # Fallback to original filename (fixes old uploads that have numeric IDs)
    if content is None and media.original_filename:
        content = nc.download_file(media.original_filename)

    if content:
        return content, content_type
    return None, None
