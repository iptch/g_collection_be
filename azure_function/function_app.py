import azure.functions as func
import logging
from PIL import Image
import io

app = func.FunctionApp()


@app.blob_trigger(arg_name="inputblob", path="card-high-res-images/{filename}",
                  connection="connectionstring")
@app.blob_output(arg_name="outputblob",
                 path="card-thumbnails/{filename}",
                 connection="connectionstring")
def BlobTrigger(inputblob: func.InputStream, outputblob: func.Out[str]):
    logging.info(f"Python blob trigger function processed blob Name: {inputblob.name}")

    image = Image.open(inputblob.read())
    image.thumbnail((100, 100))

    with io.BytesIO() as output:
        image.save(output, format="GIF")
        contents = output.getvalue()
        outputblob.set(f"{contents}")