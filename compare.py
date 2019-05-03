import json
import math
import os
import sys
import zipfile
import shutil
from PIL import Image
from PIL import ImageChops


def rms_diff(im1, im2):
    diff = ImageChops.difference(im1, im2)
    h = diff.histogram()
    sq = (value*((idx % 256)**2) for idx, value in enumerate(h))
    sum_of_squares = sum(sq)
    rms = math.sqrt(sum_of_squares/float(im1.size[0] * im1.size[1]))
    return rms


def image_compare(path_source, path_compare, out_path):
    src_image = Image.open(path_source)
    cmp_image = Image.open(path_compare)

    result = ImageChops.difference(src_image, cmp_image)
    result.thumbnail((360, 640))

    rms = rms_diff(Image.open(path_source), Image.open(path_compare)) / 255.0 * 100

    src_image.thumbnail((360, 640))

    color = Image.new('RGBA', result.size, (0, 255, 0, 0))
    mask = Image.new('RGBA', result.size, (0, 0, 0, 0))
    mask.paste(result)
    mask = mask.convert('L').point(lambda p: p > 0 and 255)
    diff = Image.composite(color, src_image, mask=mask)
    if not os.path.isdir('out'):
        os.mkdir('out')
    out_path = os.path.join('out', out_path)
    diff.save(out_path)
    print('  diff:%3d%% | \'%s\' ? \'%s\' -> \'%s\'' % (rms, path_source, path_compare, out_path))

    return {'diff': int(rms), 'src': path_source, 'cmp': path_compare, 'out': out_path}


def show_help():
    print 'GBKSoft image compare utility help:'
    print 'python compare.py --help - show this message'
    print 'Usage: python compare.py path/to/reference/file path/to/compare/file path/to/output/file'
    print ' First file is full path original file\n' \
          ' second file (full path) will be compared to first one\n' \
          ' third file - filename only output where to save image diff.'
    print 'python compare.py -c /path/to/config/file\n' \
          'compare several files in one batch, file format is one arg per line:\n' \
          'path/to/reference/file;path/to/compare/file;path/to/output/file'


def parse_config(config_file):
    fp = open(config_file, 'rb')
    files = fp.read().replace('\r\n', '\n').split('\n')
    fp.close()
    return files


def compare_files(files):
    report = []
    for f in files:
        path = f.split(';')
        if not os.path.isdir('src'):
            os.makedirs('src')
        if not os.path.isdir('cmp'):
            os.makedirs('cmp')
        shutil.copy(path[0], 'src/')
        shutil.copy(path[1], 'cmp/')

        file_src = os.path.join('src', os.path.basename(path[0]))
        file_cmp = os.path.join('cmp', os.path.basename(path[1]))

        result = image_compare(file_src, file_cmp, path[2])
        result['orig'] = path[0]
        report.append(result)

    build_report(report)


def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for f in files:
            ziph.write(os.path.join(root, f))


def build_report(report):
    fp = open('base_report/base_report.html', 'rb')
    rep = fp.read()
    fp.close()
    json_string = json.dumps(report)
    rep = rep.replace('/**/[]/**/', json_string)

    report_path = 'report.html'
    fp = open(report_path, 'wb+')
    fp.write(rep)
    fp.close()

    json_path = 'report.json'
    fp = open(json_path, 'wb+')
    fp.write(json_string)
    fp.close()

    zip_name = 'report.zip'
    zf = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    zf.write(report_path)
    zf.write(json_path)
    zipdir('cmp/', zf)
    zipdir('src/', zf)
    zipdir('out/', zf)
    zf.close()
    os.remove(report_path)
    os.remove(json_path)
    shutil.rmtree('src')
    shutil.rmtree('cmp')
    shutil.rmtree('out')

    print('Done generating report: %s' % zip_name)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '-c':
        print ('Done comparing:')
        compare_files(parse_config(sys.argv[2]))
        exit()
    if len(sys.argv) < 4 or (len(sys.argv) == 1 and (sys.argv[1] == '-h' or sys.argv[1] == '--help')):
        show_help()
        exit()
    print ('Done comparing:')
    compare_files([';'.join([sys.argv[1], sys.argv[2], sys.argv[3]])])
