import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional

class CloudinaryService:
    @staticmethod
    def upload_image(file_content: bytes, folder: str, public_id: str) -> Optional[str]:
        """
        Upload image to Cloudinary

        Args:
            file_content: Image binary content
            folder: Cloudinary folder path
            public_id: Public ID for the image

        Returns:
            Secure URL of uploaded image or None if upload fails
        """
        try:
            response = cloudinary.uploader.upload(
                file_content,
                folder=folder,
                public_id=public_id,
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return None

    @staticmethod
    def delete_image(public_id: str) -> bool:
        """
        Delete image from Cloudinary

        Args:
            public_id: Public ID of the image to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            print(f"Error deleting from Cloudinary: {e}")
            return False
