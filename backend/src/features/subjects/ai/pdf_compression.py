from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from decouple import config

logger = logging.getLogger(__name__)

DPI_THRESHOLD = int(str(config("PDF_COMPRESS_DPI_THRESHOLD", default="150")).strip())
DPI_TARGET = int(str(config("PDF_COMPRESS_DPI_TARGET", default="110")).strip())
QUALITY = int(str(config("PDF_COMPRESS_QUALITY", default="75")).strip())
TIMEOUT_SECONDS = int(str(config("PDF_COMPRESS_TIMEOUT", default="600")).strip())
ATTEMPTS = 3
MIN_GAIN = 0.9


def _rewrite(source: Path, target: Path) -> None:
    import pymupdf

    document = pymupdf.open(str(source))
    try:
        document.rewrite_images(
            dpi_threshold=DPI_THRESHOLD, dpi_target=DPI_TARGET, quality=QUALITY
        )
        document.save(str(target), garbage=4, deflate=True, clean=True)
    finally:
        document.close()


def compress_pdf(source: Path, target: Path) -> bool:
    """Recomprime as imagens do PDF. Roda isolado porque o MuPDF aborta o processo
    com SIGSEGV de forma intermitente em arquivos grandes; a falha é transitória e
    não pode derrubar o worker."""
    original = source.stat().st_size

    for attempt in range(1, ATTEMPTS + 1):
        result = subprocess.run(
            [sys.executable, "-m", __spec__.name, str(source), str(target)],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode == 0 and target.exists():
            break
        logger.warning(
            "compress_pdf: tentativa %d/%d falhou em %s (returncode=%s) %s",
            attempt,
            ATTEMPTS,
            source.name,
            result.returncode,
            result.stderr.decode(errors="replace")[-300:],
        )
        target.unlink(missing_ok=True)
    else:
        return False

    compressed = target.stat().st_size
    if compressed >= original * MIN_GAIN:
        logger.info(
            "compress_pdf: ganho insuficiente em %s (%d -> %d bytes)",
            source.name,
            original,
            compressed,
        )
        target.unlink(missing_ok=True)
        return False

    logger.info(
        "compress_pdf: %s %d -> %d bytes (%d%%)",
        source.name,
        original,
        compressed,
        100 * compressed // original,
    )
    return True


if __name__ == "__main__":
    _rewrite(Path(sys.argv[1]), Path(sys.argv[2]))
