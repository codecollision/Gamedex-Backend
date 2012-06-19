from google.appengine.api import urlfetch

from django.http import HttpResponse

from lxml.cssselect import CSSSelector
from lxml import etree

from boto.s3.connection import S3Connection

import logging
import re

# base url
S3_URL = 'https://s3.amazonaws.com/'
# site bucket
ASSET_BUCKET = 's3.gamedex.net'

# S3 Properties
AWS_HEADERS = {
    'Cache-Control': 'max-age=2592000,public'
}
AWS_ACL = 'public-read'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# COPY ASSETS TO S3
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def copyAssetsToS3(s3conn):

    s3conn = S3Connection('0JVZGYMSKN59DPNKRGR2', 'AImptXlEmeKcQREmkl6qCEomGnm7aoueigTOJlmL', is_secure=False)

    # assets
    assetList = [
        'http://static.gamedex.net/images/bg_tile.png',
        'http://static.gamedex.net/images/bg_tile_light.png',
        'http://static.gamedex.net/images/bg_tile_light2.png',
        'http://static.gamedex.net/images/chosen-sprite.png',
        'http://static.gamedex.net/images/glyphicons-halflings-white.png',
        'http://static.gamedex.net/images/glyphicons-halflings.png',
        'http://static.gamedex.net/images/header_tile.png',
        'http://static.gamedex.net/images/jquery.ui.stars.gif',
        'http://static.gamedex.net/images/loading_bar.gif',
        'http://static.gamedex.net/images/logo.png',
        'http://static.gamedex.net/images/logo_small.png',
        'http://static.gamedex.net/images/no_selection_placeholder.png',
        'http://static.gamedex.net/images/select2.png',
        'http://static.gamedex.net/images/site_description.png',
        'http://static.gamedex.net/images/site_features.png',
        'http://static.gamedex.net/images/site_features_detail.png',
        'http://static.gamedex.net/images/sprites.png',
        'http://static.gamedex.net/images/title_bar_center.png',
        'http://static.gamedex.net/images/title_bar_dark_center.png',
        'http://static.gamedex.net/images/title_bar_dark_left.png',
        'http://static.gamedex.net/images/title_bar_dark_right.png',
        'http://static.gamedex.net/images/title_bar_left.png',
        'http://static.gamedex.net/images/title_bar_right.png',
        'http://static.gamedex.net/images/video-js.png',
        'http://static.gamedex.net/css/bootstrap.css',
        'http://static.gamedex.net/css/tmz.css',
        'http://static.gamedex.net/js/full.js'
    ]

    # iterate urls and copy to s3
    for url in assetList:
        copyUrlToS3(url, s3conn)

    return HttpResponse('done', mimetype='text/html')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# COPY URL TO S3
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def copyUrlToS3(url, s3conn):

    # get s3 bucket
    bucket = s3conn.get_bucket(ASSET_BUCKET, validate=False)

    # get filename and extension
    fileName = url.split('/')[-1]
    extension = fileName.split('.')[-1]

    # load url
    response = urlfetch.fetch(url, None, 'GET', {}, False, False, 30)

    # create new S3 key, set mimetype and Expires header
    k = bucket.new_key(fileName)
    if (extension == 'jpg'):
        mimeType = 'image/jpeg'
    elif (extension == 'png'):
        mimeType = 'image/png'
    elif (extension == 'gif'):
        mimeType = 'image/gif'
    elif (extension == 'css'):
        mimeType = 'text/css'
    elif (extension == 'js'):
        mimeType = 'application/javascript'

    k.content_type = mimeType

    # write file from response string set public read permission
    k.set_contents_from_string(response.content, headers=AWS_HEADERS, replace=True, policy=AWS_ACL)
    k.set_acl('public-read')

    # s3 url
    return S3_URL + ASSET_BUCKET + '/' + fileName


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# gamewallpapers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def gamewallpapers(request):

    page = 0
    if 'page' in request.GET:
        page = request.GET.get('page')

    offset = 14 * int(page)

    url = 'http://www.gamewallpapers.com/index.php?start=%s&filterplatform=' % offset

    # fetch(url, payload=None, method=GET, headers={}, allow_truncated=False, follow_redirects=True, deadline=None, validate_certificate=None)
    # allow 30 seconds for response
    pageResponse = urlfetch.fetch(url, None, 'GET', {}, False, False, 30)

    if pageResponse.status_code == 200:

        html = etree.HTML(pageResponse.content)

        pageSel = CSSSelector('a.tooltip')
        pageLinks = []

        # mine page links to game pages
        for pageLink in pageSel(html):

            try:
                url = pageLink.get('href').strip()
                pageLinks.append(url)

            except IndexError:
                logging.error('IndexError')

        # find max res wallpaper links
        linksSel = CSSSelector('a')

        wallpaperLinks = []

        # iterate game page links
        for link in pageLinks:

            if link.find('cgwallpapers') == -1:

                # fetch game page
                gamepageResponse = urlfetch.fetch(link, None, 'GET', {}, False, False, 30)
                html = etree.HTML(gamepageResponse.content)

                # for each wallpaper link in linksContainer
                for wallpaperLink in linksSel(html):

                    if wallpaperLink.text != None:

                        linkText = wallpaperLink.text.encode('utf-8')

                        if (linkText.find('1920x1200') != -1):
                            linkURL = wallpaperLink.get('href').strip()
                            wallpaperLinks.append(linkURL)

        # construct final links
        outputLinks = []
        # http://www.gamewallpapers.com/members/getwallpaper.php?wallpaper=wallpaper_dirt_showdown_02_2560x1600.jpg
        for link in wallpaperLinks:

            nameMatches = re.search('wallpaper[a-z|_|.|0-9]*', link, flags=0)

            if nameMatches:
                wallpaperName = nameMatches.group()
                wallpaperName = wallpaperName.replace('1920x1200', '2560x1600')

                # create output link
                outputLink = '<a href="http://www.gamewallpapers.com/members/getwallpaper.php?wallpaper=%s">%s</a>' % (wallpaperName, wallpaperName)
                outputLinks.append(outputLink)

    # join list to html doc string
    html = '<br>'.join(outputLinks)

    return HttpResponse(html, mimetype='text/html')


#
# http://wallbase.cc/toplist/0/213/eqeq/0x0/0/100/60/3d
#                            start index
#                              #categories (general/highres/manga)
#                                             sfw/sketchy/nsfw
#                                                 thumbs per requests (60 max)
