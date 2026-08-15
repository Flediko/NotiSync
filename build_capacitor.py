import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NotiSyncBuilder")

def build():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(src_dir, "www")
    
    # 1. Clean previous build
    if os.path.exists(dist_dir):
        logger.info(f"Cleaning existing bundle directory: {dist_dir}")
        shutil.rmtree(dist_dir)
        
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "static"), exist_ok=True)
    
    # 2. Copy static folder contents
    static_src = os.path.join(src_dir, "static")
    static_dist = os.path.join(dist_dir, "static")
    logger.info(f"Copying static files from {static_src} to {static_dist}")
    
    if os.path.exists(static_src):
        for item in os.listdir(static_src):
            s = os.path.join(static_src, item)
            d = os.path.join(static_dist, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    else:
        logger.error("Source static folder not found!")
        return False
        
    # 3. Copy templates/index.html to www/index.html
    html_src = os.path.join(src_dir, "templates", "index.html")
    html_dist = os.path.join(dist_dir, "index.html")
    
    if os.path.exists(html_src):
        logger.info(f"Copying and updating index.html to {html_dist}")
        with open(html_src, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Ensure any remaining absolute static paths are replaced with relative ones
        content = content.replace('href="/static/', 'href="static/')
        content = content.replace('src="/static/', 'src="static/')
        content = content.replace('href=\'/static/', 'href=\'static/')
        content = content.replace('src=\'/static/', 'src=\'static/')
        
        with open(html_dist, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        logger.error("Source templates/index.html not found!")
        return False
        
    logger.info("Capacitor static assets bundle successfully built in /www folder!")
    return True

if __name__ == "__main__":
    build()
