from json import dump
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

from odoo import models


class ebay_sdk(models.Model):
    _name = 'ebay.sdk'


def uploadPictureFromFilesystem(opts, filepath):
    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        # pass in an open file
        # the Requests module will close the file
        files = {'file': ('EbayImage', open(filepath, 'rb'))}

        pictureData = {
            "WarningLevel": "High",
            "PictureName": "WorldLeaders"
        }

        api.execute('UploadSiteHostedPictures', pictureData, files=files)
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())
