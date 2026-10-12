import json
from pathlib import Path
import sys
from .documents import extract_pages
from .errors import DomainError


if __name__=="__main__":
    try:
        if sys.argv[5]=="1":
            from .config import Settings,ROOT
            from .model_integrity import verify_artifacts
            settings=Settings()
            entry=json.loads((ROOT/"verification/ocr-artifacts.json").read_text())
            verify_artifacts(settings.ocr_data_path,entry,settings.ocr_model_revision)
        path=Path(sys.argv[1])
        if path.stat().st_size>20*1024*1024:raise DomainError("UPLOAD_TOO_LARGE",413)
        pages=extract_pages(path.read_bytes(),sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),ocr=sys.argv[5]=="1",ocr_language=sys.argv[6])
        sys.stdout.buffer.write(json.dumps(pages,ensure_ascii=False).encode("utf-8"))
    except DomainError as error:
        sys.stdout.buffer.write(json.dumps({"error":error.code}).encode("utf-8"))
        sys.exit(1)
    except Exception:
        sys.stdout.buffer.write(b'{"error":"EXTRACTION_FAILED"}')
        sys.exit(1)
