import torch
import common
from common import gaussian, normilize, nhwc_to_nchw, to_np
import numpy as np
from datasets import DatasetFromFolder
from torch.utils.data import DataLoader
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pybm3d

from convsparse_net import LISTAConvDict
from datasets import  DatasetFromNPZ
import arguments

USE_CUDA = torch.cuda.is_available()

def plot_res(img, img_n, res, name, log_path, other_res=None):
    """Plot clean/noisy/orig images
    """

    img = np.squeeze(img)
    img_n = np.squeeze(img_n)
    res = np.squeeze(res)

    if other_res is not None:
        sub_typ = 221
    else:
        sub_typ = 131

    plt.subplot(sub_typ)
    plt.imshow(img, cmap='gray')
    plt.title('original')
    plt.gca().axis('off')

    plt.subplot(sub_typ + 1)
    plt.imshow(img_n, cmap='gray')
    plt.title('noise {:.2f} db'.format(common.psnr(img, img_n)))
    plt.gca().axis('off')

    plt.subplot(sub_typ + 2)
    plt.imshow(res, cmap='gray')
    plt.title('ours psnr {:.2f} db'.format(common.psnr(img, res)))
    plt.gca().axis('off')

    if other_res is not None:
        plt.subplot(sub_typ + 3)
        plt.imshow(res, cmap='gray')
        plt.title('other psnr {:.2f} db'.format(common.psnr(img, other_res)))
        plt.gca().axis('off')
    plt.savefig(os.path.join(log_path, 'res_{}'.format(name)))
    plt.clf()

def restore_model(model_args, saved_model_path):
    model = LISTAConvDict(
        num_input_channels=model_args['num_input_channels'],
        num_output_channels=model_args['num_output_channels'],
        kc=model_args['kc'],
        ks=model_args['ks'],
        ista_iters=model_args['ista_iters'],
        iter_weight_share=model_args['iter_weight_share'],
        share_decoder=model_args['share_decoder']
    )
    common.load_eval(saved_model_path, model)
    return model

def create_famouse_dataset(test_path, noise):
    def pre_process_fn(_x): return normilize(_x, 255)
    def input_process_fn(_x): return gaussian(_x, is_training=True, mean=0, stddev=normilize(noise, 255))

    return DatasetFromFolder(
                test_path,
                pre_transform=pre_process_fn,
                use_cuda=USE_CUDA,
                inputs_transform=input_process_fn
            )


def test(args, saved_model_path, noise, testset_path):
    """Run predictable test
    """
    torch.manual_seed(7)


    testset = create_dataset(testset_path, noise)
    file_names = testset.image_filenames
    test_loader = DataLoader(testset)

    model = restore_model(args, saved_model_path)

    if USE_CUDA:
        model = model.cuda()

    psnrs = []
    res_array = []
    idx = 0
    for test_data, test_name in zip(test_loader, file_names):
        img, img_n = test_data
        output, _ = model(img_n)

        b = args['ks'] // 2

        np_img = to_np(img)[0, 0, b:-b, b:-b]
        np_output = np.clip(to_np(output)[0, 0, b:-b, b:-b], 0, 1)
        np_img_n = to_np(img_n)[0, 0, b:-b, b:-b]

        bm3d_img =\
                pybm3d.bm3d.bm3d(to_np(img_n)[0, 0, ...], normilize(noise, 255))[b:-b, b:-b]

        bm3d_psnr = common.psnr(np_img, bm3d_img)
        ours_psnr = common.psnr(np_img, np_output, False)
        psnrs.append({'ours': ours_psnr, 'bm3d': bm3d_psnr})
        res_array.append((np_img, np_img_n, np_output, bm3d_img))

        print('Test Image {} psnr ours {} bm3d {}'.format(test_name, ours_psnr,
                                                   bm3d_psnr))
        idx += 1

    print('Avg psnr ours: {} other: {}'.format(np.mean([p['ours'] for p in psnrs]),
                                               np.mean([p['bm3d'] for p in psnrs])
                                              )
         )
def test(args, saved_model_path, noise, testset_path):
    """Run predictable test
    """
    torch.manual_seed(7)


    testset = create_famouse_dataset(testset_path, noise)
    file_names = testset.image_filenames
    test_loader = DataLoader(testset)

    model = restore_model(args, saved_model_path)

    if USE_CUDA:
        model = model.cuda()

    return psnrs, res_array, file_names

def _test(args_file):
    _args = arguments.load_args(args_file)
    test_args = _args['test_args']
    model_args = _args['model_args']

    model_path = test_args['load_path']
    tst_ims = test_args["testset_path"]
    noise = test_args['noise']

    log_dir = os.path.dirname(model_path)
    psnr, res, file_names = test(model_args, model_path, noise, tst_ims)
    for f_name, ims in zip(file_names, res):
        plot_res(ims[0], ims[1], ims[2], f_name, log_dir, ims[3])

def main():
    """Run test on trained model.
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--arg_file', default='./my_args.json')
    args_file = parser.parse_args().arg_file

    _test(args_file)

if __name__ == '__main__':
    main()

