import os
from urllib.parse import urlparse


def is_file_link(url: str, link_element=None) -> tuple[bool, str]:
    """
    Check if a URL points to a file rather than a webpage.
    
    Args:
        url: The URL to check
        link_element: Optional BeautifulSoup link element to check for download attribute
    
    Returns:
        tuple[bool, str]: (is_file, extension)
            - is_file: True if URL is a file link
            - extension: The file extension (e.g., '.pdf') or descriptive string
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check for download attribute if link element provided
    if link_element and link_element.has_attr('download'):
        return True, 'download'
    
    # Extract extension from path
    _, extension = os.path.splitext(path)
    
    # If no extension or common webpage extensions, it's likely a webpage
    webpage_extensions = [
        '.html', '.htm', '.php', '.asp', '.aspx', '.jsp',
        '.shtml', '.xhtml', '.jhtml',  # Server-side HTML variants
        '.cfm', '.cgi',                 # ColdFusion, CGI scripts
        '.do', '.action',               # Struts/Java web frameworks
        '.pl', '.py', '.rb',            # Script-based web pages (Perl, Python, Ruby)
    ]
    
    if not extension or extension in webpage_extensions:
        return False, ''
    
    # Common file extensions to skip
    file_extensions = [
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
        '.txt', '.csv', '.rtf', '.odt', '.ods', '.odp',
        # Archives
        '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2', '.tgz', '.tar.gz',
        '.tar.bz2', '.xz', '.z',
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', 
        '.ico', '.tiff', '.tif', '.heic', '.heif',
        # Media - Audio
        '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma',
        # Media - Video
        '.mp4', '.avi', '.mov', '.webm', '.flv', '.wmv', '.mkv', 
        '.m4v', '.mpg', '.mpeg', '.3gp',
        # Code/Data
        '.json', '.xml', '.sql', '.yaml', '.yml', '.toml', '.ini', '.conf',
        # Executables/Installers
        '.exe', '.dmg', '.pkg', '.deb', '.rpm', '.msi', '.app',
        # Scripts (when downloadable, not server-executed)
        '.sh', '.bat', '.cmd', '.ps1',
        # Fonts
        '.ttf', '.otf', '.woff', '.woff2', '.eot',
        # Other common files
        '.iso', '.bin', '.dat', '.db', '.log',
    ]
    
    if extension in file_extensions:
        return True, extension
    
    # If extension exists but not in our lists, assume it's a file to be safe
    # This prevents attempting to parse unknown file types
    return True, extension
