import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Set

# Tracking query parameters to strip from URLs
TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "twclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
    "spm",
    "feature",
    "si",
}


def canonicalize_url(raw_url: str) -> str:
    """
    Normalizes a URL by:
    - Trimming whitespace
    - Lowercasing scheme and netloc/domain
    - Removing standard default ports (:80, :443)
    - Stripping known marketing/tracking query parameters
    - Sorting remaining query parameters deterministically
    - Stripping fragment (#...)
    - Normalizing trailing slashes on paths
    """
    if not raw_url or not isinstance(raw_url, str):
        return ""

    url = raw_url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return raw_url.strip().lower()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path (lowercase and remove trailing slash)
    path = (parsed.path or "/").lower()
    # Collapse multiple slashes
    path = re.sub(r"/+", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Filter and sort query parameters
    query_params = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_params = sorted(
        [(k.lower(), v) for k, v in query_params if k.lower() not in TRACKING_PARAMS]
    )
    query_string = urlencode(filtered_params)

    # Reconstruct URL without fragment
    return urlunparse((scheme, netloc, path, "", query_string, ""))


def compute_url_hash(canonical_url: str) -> str:
    """Computes SHA-256 hash of canonical URL."""
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


def compute_content_hash(text: str) -> str:
    """
    Computes a content hash by normalizing whitespace, stripping dynamic timestamps,
    and generating a deterministic SHA-256 digest.
    """
    if not text:
        return hashlib.sha256(b"").hexdigest()

    # Normalize unicode whitespace and collapse multiple spaces/newlines
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    # Remove common ephemeral date/time patterns for announcement hash consistency
    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", cleaned)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def normalize_entity_name(name: str) -> str:
    """Normalizes model/provider/service names for comparison."""
    if not name:
        return ""
    # Strip excess punctuation and standardize casing
    cleaned = re.sub(r"[^\w\s\-\.\+]", "", name.strip())
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def extract_domain(url: str) -> str:
    """Extracts base domain from URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        # Strip www. prefix for cleaner domain tracking
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or "unknown"
    except Exception:
        return "unknown"
