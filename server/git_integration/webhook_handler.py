# server/git_integration/webhook_handler.py
import hashlib
import hmac
from typing import Optional

from fastapi import Depends, HTTPException, Request

from logger import logger

from . import git_config


async def verify_github_signature(
    request: Request,
    x_hub_signature_256: Optional[str],
):
    """
    Verifies the webhook signature from GitHub.
    This function now expects headers to be passed in manually.
    """
    if not git_config.GIT_WEBHOOK_SECRET:
        logger.error("verify_github_signature called without a configured secret.")
        raise HTTPException(status_code=500, detail="Server configuration error.")

    if x_hub_signature_256 is None:
        logger.error("Webhook received without X-Hub-Signature-256 header.")
        raise HTTPException(
            status_code=400, detail="Missing X-Hub-Signature-256 header."
        )

    # Get the raw request body
    body = await request.body()

    # Compute the expected signature
    try:
        expected_signature = (
            "sha256="
            + hmac.new(
                git_config.GIT_WEBHOOK_SECRET.encode(), body, hashlib.sha256
            ).hexdigest()
        )
    except Exception as e:
        logger.error(f"Error computing HMAC signature: {e}")
        raise HTTPException(status_code=500, detail="Could not compute signature.")

    # Compare signatures securely
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        logger.error("Webhook signature mismatch.")
        raise HTTPException(status_code=403, detail="Invalid signature.")

    logger.debug("Webhook signature verified successfully.")


# A dependency that combines signature verification with enabled check
def get_webhook_dependency():
    if git_config.GIT_WEBHOOK_SECRET:
        return Depends(verify_github_signature)
    return None
