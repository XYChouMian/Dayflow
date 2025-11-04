"""Application update manager."""

import logging
import requests
from typing import Optional, Dict
from packaging import version

logger = logging.getLogger(__name__)


class UpdateManager:
    """Manage application updates via GitHub releases."""

    def __init__(self, repo_owner: str, repo_name: str, current_version: str):
        """
        Initialize update manager.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            current_version: Current application version
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def check_for_updates(self) -> Optional[Dict]:
        """
        Check if a new version is available.

        Returns:
            Dictionary with update info or None if no update
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data.get("tag_name", "").lstrip("v")

            if not latest_version:
                logger.warning("Could not determine latest version")
                return None

            # Compare versions
            if version.parse(latest_version) > version.parse(self.current_version):
                logger.info(f"Update available: {latest_version}")

                return {
                    "version": latest_version,
                    "name": release_data.get("name", ""),
                    "description": release_data.get("body", ""),
                    "download_url": self._get_windows_download_url(release_data),
                    "published_at": release_data.get("published_at", ""),
                }

            logger.info("Application is up to date")
            return None

        except requests.RequestException as e:
            logger.error(f"Error checking for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking updates: {e}", exc_info=True)
            return None

    def _get_windows_download_url(self, release_data: Dict) -> Optional[str]:
        """
        Extract Windows installer download URL from release data.

        Args:
            release_data: GitHub release API response

        Returns:
            Download URL or None
        """
        assets = release_data.get("assets", [])

        for asset in assets:
            name = asset.get("name", "").lower()
            if "windows" in name or name.endswith(".exe") or name.endswith(".msi"):
                return asset.get("browser_download_url")

        # Fallback to first asset
        if assets:
            return assets[0].get("browser_download_url")

        return None

    def download_update(self, download_url: str, save_path: str) -> bool:
        """
        Download update file.

        Args:
            download_url: URL to download from
            save_path: Local path to save file

        Returns:
            True if successful
        """
        try:
            logger.info(f"Downloading update from: {download_url}")

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")

            logger.info(f"Update downloaded to: {save_path}")
            return True

        except Exception as e:
            logger.error(f"Error downloading update: {e}", exc_info=True)
            return False
