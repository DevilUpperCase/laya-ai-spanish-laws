"""Clearly synthetic private PDF for browser workflow checks; never ingest as legislation."""
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    path=ROOT/"private-data/browser-synthetic.pdf"
    path.parent.mkdir(exist_ok=True)
    document=pymupdf.open()
    document.new_page().insert_text((50,50),"Synthetic private test only: vivienda y arrendamiento. Not legal evidence.")
    document.save(path)
    print("Synthetic private browser fixture prepared.")
