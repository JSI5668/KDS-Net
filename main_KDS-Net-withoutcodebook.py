import os
os.environ['CUDA_LAUNCH_BLOCKING'] = "1"

from tqdm import tqdm
import network
import utils
import os
import random
import argparse
import numpy as np
import sdfsdf as pd
import torch.nn.functional as F

from torch import optim

from data_RGB import get_training_data, get_validation_data

from torch.utils import data
from datasets import  Camvid_Edge, Kitti_sample, Minicity, Camvid_proposed, Camvid_sample, Camvid_Edge_laplacian, Minicity_Edge
from utils import ext_transforms as et
from metrics import StreamSegMetrics
from torchsummary import summary
import torch
import torch.nn as nn
from utils.visualizer import Visualizer
from torchsummaryX import summary
from network.unet import UNet_my
from network.unet import UNet_my_2
from network.unet import EdgeNet
from network.unet import UNet_my_3
from network.unet import W_Net
from network.unet import MHNet_my, MHNet_my_2
from network.unet import UNet_3Plus, UNet_3Plus_my, UNet_chae, encoder_my_2, decoder_my_2
import segmentation_models_pytorch as smp

from PIL import Image
import matplotlib
import matplotlib.pyplot as plt
from typing import Optional
from utils.loss import Edge_PerceptualLoss

from torchvision.models.feature_extraction import get_graph_node_names
from torchvision.models.feature_extraction import create_feature_extractor

from ptflops import get_model_complexity_info

# PATH_1 = 'E:/Second_paper/Checkpoint/Camvid/EdgeNet_2_model/model.pt'
# model_Edge = torch.load(PATH_1)
# PATH_1 = 'E:/Second_paper/Checkpoint/Camvid/EdgeNet_Secondfold_model/model.pt'
# model_Edge = torch.load(PATH_1)

# PATH_1 = 'E:/Second_paper/Checkpoint/Kitti/EdgeNet_Sobel/Firstfold_model/model.pt'
# model_Edge = torch.load(PATH_1)
PATH_1 = 'E:/Second_paper/Checkpoint/Kitti/EdgeNet_Sobel/Secondfold_model/model.pt'
model_Edge = torch.load(PATH_1)

# PATH_1 = 'E:/Second_paper/Checkpoint/Camvid/EdgeNet_2_model/model.pt'
# model_Edge = torch.load(PATH_1)

train_nodes, eval_nodes = get_graph_node_names(model_Edge)

train_return_nodes={
    train_nodes[3]: 'f1',
    train_nodes[6]: 'f2',
    train_nodes[7]: 'f3'
}

eval_return_nodes={
    train_nodes[3]: 'f1',
    train_nodes[6]: 'f2',
    train_nodes[7]: 'f3'
}

feature_extract = create_feature_extractor(model_Edge, train_return_nodes)
# print(feature_extract)
#python -m visdom.server

def label_to_one_hot_label(
        labels: torch.Tensor,
        num_classes: int,
        device: Optional[torch.device] = 'cuda',
        dtype: Optional[torch.dtype] = None,
        eps: float = 1e-6,
        ignore_index=255,
) -> torch.Tensor:
    r"""Convert an integer label x-D tensor to a one-hot (x+1)-D tensor.

    Args:
        labels: tensor with labels of shape :math:`(N, *)`, where N is batch size.
          Each value is an integer representing correct classification.
        num_classes: number of classes in labels.
        device: the desired device of returned tensor.
        dtype: the desired data type of returned tensor.

    Returns:
        the labels in one hot tensor of shape :math:`(N, C, *)`,

    Examples:
        >>> labels = torch.LongTensor([
                [[0, 1],
                [2, 0]]
            ])
        >>> one_hot(labels, num_classes=3)
        tensor([[[[1.0000e+00, 1.0000e-06],
                  [1.0000e-06, 1.0000e+00]],

                 [[1.0000e-06, 1.0000e+00],
                  [1.0000e-06, 1.0000e-06]],

                 [[1.0000e-06, 1.0000e-06],
                  [1.0000e+00, 1.0000e-06]]]])

    """
    shape = labels.shape
    # one hot : (B, C=ignore_index+1, H, W)
    one_hot = torch.zeros((shape[0], ignore_index + 1) + shape[1:], device=device, dtype=dtype)

    # labels : (B, H, W)
    # labels.unsqueeze(1) : (B, C=1, H, W)
    # one_hot : (B, C=ignore_index+1, H, W)
    one_hot = one_hot.scatter_(1, labels.unsqueeze(1), 1.0) + eps

    # ret : (B, C=num_classes, H, W)
    ret = torch.split(one_hot, [num_classes, ignore_index + 1 - num_classes], dim=1)[0]

    return ret

def get_argparser():
    parser = argparse.ArgumentParser()

    # Datset Options
    # parser.add_argument("--data_root", type=str, default='./datasets/data',
    #                     help="path to Dataset")
    parser.add_argument("--data_root", type=str, default='D:/Dataset/Camvid/camvid_sample_2/blur_new/camvid_firstfold_10_3_random_params',
                        help="path to Dataset")  ##crop size 바꿔주기
    # parser.add_argument("--data_root", type=str,
    #                     default='D:/Dataset/Camvid/camvid_original_240',
    #                      help="path to Dataset")   ##crop size 바꿔주기
    parser.add_argument("--dataset", type=str, default='camvid_sample',
                        choices=['camvid_sample', 'Edge', 'Edge_laplacian', 'camvid', 'camvid_sample', 'mini_city', 'kitti_sample', 'camvid_proposed', 'Edge_minicity' ], help='Name of dataset')
    parser.add_argument("--num_classes", type=int, default=None,
                        help="num classes (default: None)")

    # Deeplab Options
    parser.add_argument("--model", type=str, default='deeplabv3plus_resnet50',
                        choices=['deeplabv3_resnet50',  'deeplabv3plus_resnet50',
                                 'deeplabv3_resnet101', 'deeplabv3plus_resnet101',
                                 'deeplabv3_mobilenet', 'deeplabv3plus_mobilenet'], help='model name')
    parser.add_argument("--separable_conv", action='store_true', default=False,
                        help="apply separable conv to decoder and aspp")
    parser.add_argument("--output_stride", type=int, default=16, choices=[8, 16])

    # Train Options
    parser.add_argument("--test_only", action='store_true', default=False)
    parser.add_argument("--save_val_results", action='store_true', default=False,
                        help="save segmentation results to \"./results\"")
    # parser.add_argument("--total_itrs", type=int, default=17e3,
    #                     help="epoch number (default: 30k)")
    # parser.add_argument("--total_itrs", type=int, default=100e3,
    #                     help="epoch number (default: 30k)")
    parser.add_argument("--total_itrs", type=int, default=55000,
                        help="epoch number (default: 30k)")
    parser.add_argument("--lr", type=float, default=0.01,
                        help="learning rate (default: 0.01)")
    parser.add_argument("--lr_policy", type=str, default='poly', choices=['poly', 'step'],
                        help="learning rate scheduler policy")
    parser.add_argument("--step_size", type=int, default=10000)
    parser.add_argument("--crop_val", action='store_true', default=False,
                        help='crop validation (default: False)')
    parser.add_argument("--batch_size", type=int, default=4,
                        help='batch size (default: 16)')
    parser.add_argument("--val_batch_size", type=int, default=1,
                        help='batch size for validation (default: 4)')
    # parser.add_argument("--crop_size", type=int, default=192) ##513
    # parser.add_argument("--crop_size", type=int, default=240)
    parser.add_argument("--crop_size", type=int, default=256)##513

    # parser.add_argument("--ckpt", default='E:/Second_paper/Checkpoint/Camvid/Blur_secondfold/SecondProposed/10_3_random/Proposed/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', type=str,
    #                     help="restore from checkpoint")
    # parser.add_argument("--ckpt",default='D:/checkpoint/Segmentation/camvid/torch_deeplabv3plus_secondfold/original/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', type=str,
    #                     help="restore from checkpoint")
    parser.add_argument("--ckpt", default='E:/Second_paper/Checkpoint/Camvid/Blur_firstfold/Second_Proposed/Proposed/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', type=str,
                        help="restore from checkpoint")
    # parser.add_argument("--ckpt", default='D:/checkpoint/Segmentation/kitti/original/secondfold/kitti/best_deeplabv3plus_resnet50_kitti_sample_os16.pth', type=str,
    #                     help="restore from checkpoint")

    # parser.add_argument("--ckpt", default='E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Proposed/best_deeplabv3plus_resnet50_kitti_sample_os16.pth', type=str,
    #                     help="restore from checkpoint")

    parser.add_argument("--ckpt_enc", default='E:/Second_paper/Checkpoint/Camvid/Blur_firstfold/main_chae/Pre_Restored/UNet2plusplus_pretrained_10_3_randomparam/Encoder/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', type=str,
                        help="restore from checkpoint")
    parser.add_argument("--ckpt_dec", default='E:/Second_paper/Checkpoint/Camvid/Blur_firstfold/main_chae/Pre_Restored/UNet2plusplus_pretrained_10_3_randomparam/Decoder/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', type=str,
                        help="restore from checkpoint")

    parser.add_argument("--continue_training", action='store_true', default=True)

    parser.add_argument("--overlay",  default=True)

    parser.add_argument("--loss_type", type=str, default='cross_entropy',
                        choices=['cross_entropy', 'focal_loss'], help="loss type (default: False)")
    parser.add_argument("--gpu_id", type=str, default='0',
                        help="GPU ID")
    parser.add_argument("--weight_decay", type=float, default=1e-4,
                        help='weight decay (default: 1e-4)')
    parser.add_argument("--random_seed", type=int, default=1,
                        help="random seed (default: 1)")
    parser.add_argument("--print_interval", type=int, default=10,
                        help="print interval of loss (default: 10)")
    parser.add_argument("--val_interval", type=int, default=55,
                        help="epoch interval for eval (default: 100)")
    # parser.add_argument("--val_interval", type=int, default=87,
    #                     help="epoch interval for eval (default: 100)")
    # parser.add_argument("--val_interval", type=int, default=55,
    #                     help="epoch interval for eval (default: 100)")
    parser.add_argument("--download", action='store_true', default=False,
                        help="download datasets")

    # PASCAL VOC Options
    parser.add_argument("--year", type=str, default='2012',
                        choices=['2012_aug', '2012', '2011', '2009', '2008', '2007'], help='year of VOC')

    # Visdom options
    parser.add_argument("--enable_vis", action='store_true', default=False,
                        help="use visdom for visualization")
    parser.add_argument("--vis_port", type=str, default='8097', #13570
                        help='port for visdom')
    parser.add_argument("--vis_env", type=str, default='main',
                        help='env for visdom')
    parser.add_argument("--vis_num_samples", type=int, default=8,
                        help='number of samples for visualization (default: 8)')
    return parser


def get_dataset(opts):
    """ Dataset And Augmentation
    """

    if opts.dataset == 'camvid_sample':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        test_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Camvid_sample(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Camvid_sample(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Camvid_sample(root=opts.data_root, split='test', transform=test_transform)


    if opts.dataset == 'kitti_sample':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Kitti_sample(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Kitti_sample(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Kitti_sample(root=opts.data_root, split='test', transform=val_transform)

    if opts.dataset == 'mini_city':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            et.ExtNormalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Minicity(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Minicity(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Minicity(root=opts.data_root, split='test', transform=val_transform)

    if opts.dataset == 'Edge_minicity':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            # et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            # et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Minicity_Edge(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Minicity_Edge(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Minicity_Edge(root=opts.data_root, split='test', transform=val_transform)

    if opts.dataset == 'Edge':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            # et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            # et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Camvid_Edge(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Camvid_Edge(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Camvid_Edge(root=opts.data_root, split='test', transform=val_transform)


    if opts.dataset == 'Edge_laplacian':
        train_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtRandomCrop(size=(opts.crop_size, opts.crop_size)),
            # et.ExtColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
            # et.ExtRandomHorizontalFlip(),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        val_transform = et.ExtCompose([
            # et.ExtResize( 512 ),
            et.ExtToTensor(),
            # et.ExtNormalize(mean=[0.485, 0.456, 0.406],
            #                 std=[0.229, 0.224, 0.225]),
        ])

        train_dst = Camvid_Edge_laplacian(root=opts.data_root, split='train', transform=train_transform)

        val_dst = Camvid_Edge_laplacian(root=opts.data_root, split='val', transform=val_transform)

        test_dst = Camvid_Edge_laplacian(root=opts.data_root, split='test', transform=val_transform)


    return train_dst, val_dst, test_dst



def validate_chae(opts, encoder, decoder, loader, device, metrics, ret_samples_ids=None):
    """Do validation and return specified samples"""
    metrics.reset()
    ret_samples = []
    if opts.overlay:
        if not os.path.exists('results'):
            os.mkdir('results')
        denorm = utils.Denormalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
        img_id = 0

    with torch.no_grad():
        for i, (images, labels) in tqdm(enumerate(loader)):

            images = images.to(device, dtype=torch.float32)
            labels = labels.to(device, dtype=torch.long)

            encoder_featuremap_1, encoder_featuremap_2, encoder_featuremap_3, encoder_featuremap_4, encoder_featuremap_5 = encoder(images)
            outputs = decoder(encoder_featuremap_1, encoder_featuremap_2, encoder_featuremap_3, encoder_featuremap_4, encoder_featuremap_5)

            preds = outputs.detach().max(dim=1)[1].cpu().numpy()
            targets = labels.cpu().numpy()

            metrics.update(targets, preds)
            if ret_samples_ids is not None and i in ret_samples_ids:  # get vis samples
                ret_samples.append(
                    (images[0].detach().cpu().numpy(), targets[0], preds[0]))

            if opts.save_val_results:
                for i in range(len(images)):
                    image = images[i].detach().cpu().numpy()
                    target = targets[i]
                    pred = preds[i]

                    image = (denorm(image) * 255).transpose(1, 2, 0).astype(np.uint8)
                    target = loader.dataset.decode_target(target).astype(np.uint8)
                    pred = loader.dataset.decode_target(pred).astype(np.uint8)

                    Image.fromarray(image).save('results/%d_image.png' % img_id)
                    Image.fromarray(target).save('results/%d_target.png' % img_id)
                    Image.fromarray(pred).save('results/%d_pred.png' % img_id)

                    fig = plt.figure()
                    plt.imshow(image)
                    plt.axis('off')
                    plt.imshow(pred, alpha=0.7)
                    ax = plt.gca()
                    ax.xaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    ax.yaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    plt.savefig('results/%d_overlay.png' % img_id, bbox_inches='tight', pad_inches=0)
                    plt.close()
                    img_id += 1

        score = metrics.get_results()
    return score, ret_samples

def slide_inference(self, model, img, args):
    h_stride, w_stride = args.test_stride
    h_crop, w_crop = args.test_crop_size
    B, _, H, W = img.shape
    num_classes = args.num_classes
    h_grids = max(H - h_crop + h_stride - 1, 0) // h_stride + 1
    w_grids = max(W - w_crop + w_stride - 1, 0) // w_stride + 1
    preds = img.new_zeros((B, num_classes, H, W))
    aux_preds = img.new_zeros((B, num_classes, H, W))
    count_mat = img.new_zeros((B, 1, H, W))
    for h_idx in range(h_grids):
        for w_idx in range(w_grids):
            y1 = h_idx * h_stride
            x1 = w_idx * w_stride
            y2 = min(y1 + h_crop, H)
            x2 = min(x1 + w_crop, W)
            y1 = max(y2 - h_crop, 0)
            x1 = max(x2 - w_crop, 0)
            crop_img = img[:, :, y1:y2, x1:x2]
            crop_seg_logit, crop_aux_logit = model(crop_img)
            preds += F.pad(crop_seg_logit,
                           (int(x1), int(preds.shape[3] - x2), int(y1), int(preds.shape[2] - y2)))

            aux_preds += F.pad(crop_aux_logit,
                               (int(x1), int(preds.shape[3] - x2), int(y1), int(preds.shape[2] - y2)))

            count_mat[:, :, y1:y2, x1:x2] += 1
    assert (count_mat == 0).sum() == 0
    if torch.onnx.is_in_onnx_export():
        count_mat = torch.from_numpy(count_mat.cpu().detach().numpy()).to(device=img.device)
    preds = preds / count_mat
    aux_preds = aux_preds / count_mat

    return preds, aux_preds

def validate(opts, model, loader, device, metrics, ret_samples_ids=None):
    """Do validation and return specified samples"""
    metrics.reset()
    ret_samples = []
    if opts.overlay:
        if not os.path.exists('results'):
            os.mkdir('results')
        denorm = utils.Denormalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
        img_id = 0

    with torch.no_grad():
        for i, (images, labels) in tqdm(enumerate(loader)):

            images = images.to(device, dtype=torch.float32)
            labels = labels.to(device, dtype=torch.long)

            outputs = model(images)
            # outputs = slide_inference(model, images)
            preds = outputs.detach().max(dim=1)[1].cpu().numpy()
            targets = labels.cpu().numpy()

            metrics.update(targets, preds)
            if ret_samples_ids is not None and i in ret_samples_ids:  # get vis samples
                ret_samples.append(
                    (images[0].detach().cpu().numpy(), targets[0], preds[0]))

            if opts.save_val_results:
                for i in range(len(images)):
                    image = images[i].detach().cpu().numpy()
                    target = targets[i]
                    pred = preds[i]

                    image = (denorm(image) * 255).transpose(1, 2, 0).astype(np.uint8)
                    target = loader.dataset.decode_target(target).astype(np.uint8)
                    pred = loader.dataset.decode_target(pred).astype(np.uint8)

                    Image.fromarray(image).save('results/%d_image.png' % img_id)
                    Image.fromarray(target).save('results/%d_target.png' % img_id)
                    Image.fromarray(pred).save('results/%d_pred.png' % img_id)

                    fig = plt.figure()
                    plt.imshow(image)
                    plt.axis('off')
                    plt.imshow(pred, alpha=0.7)
                    ax = plt.gca()
                    ax.xaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    ax.yaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    plt.savefig('results/%d_overlay.png' % img_id, bbox_inches='tight', pad_inches=0)
                    plt.close()
                    img_id += 1

        score = metrics.get_results()
    return score, ret_samples

def val_validate(opts, model, loader, device, metrics, ret_samples_ids=None):
    """Do validation and return specified samples"""
    metrics.reset()
    ret_samples = []
    if opts.overlay:
        if not os.path.exists('results'):
            os.mkdir('results')
        denorm = utils.Denormalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
        img_id = 0

    with torch.no_grad():
        interval_loss = 0
        criterion = nn.CrossEntropyLoss(ignore_index=255, reduction='mean')
        for i, (images, labels) in tqdm(enumerate(loader)):

            images = images.to(device, dtype=torch.float32)
            labels = labels.to(device, dtype=torch.long)

            outputs = model(images)
            preds = outputs.detach().max(dim=1)[1].cpu().numpy()
            targets = labels.cpu().numpy()

            metrics.update(targets, preds)

            # optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)

            np_loss = loss.detach().cpu().numpy()
            interval_loss += np_loss

            if ret_samples_ids is not None and i in ret_samples_ids:  # get vis samples
                ret_samples.append(
                    (images[0].detach().cpu().numpy(), targets[0], preds[0]))

            if opts.save_val_results:
                for i in range(len(images)):
                    image = images[i].detach().cpu().numpy()
                    target = targets[i]
                    pred = preds[i]

                    image = (denorm(image) * 255).transpose(1, 2, 0).astype(np.uint8)
                    target = loader.dataset.decode_target(target).astype(np.uint8)
                    pred = loader.dataset.decode_target(pred).astype(np.uint8)

                    Image.fromarray(image).save('results/%d_image.png' % img_id)
                    Image.fromarray(target).save('results/%d_target.png' % img_id)
                    Image.fromarray(pred).save('results/%d_pred.png' % img_id)

                    fig = plt.figure()
                    plt.imshow(image)
                    plt.axis('off')
                    plt.imshow(pred, alpha=0.7)
                    ax = plt.gca()
                    ax.xaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    ax.yaxis.set_major_locator(matplotlib.ticker.NullLocator())
                    plt.savefig('results/%d_overlay.png' % img_id, bbox_inches='tight', pad_inches=0)
                    plt.close()
                    img_id += 1

        score = metrics.get_results()
    return score, ret_samples, interval_loss

def main():
    opts = get_argparser().parse_args()
    if opts.dataset.lower() == 'voc':
        opts.num_classes = 21
    elif opts.dataset.lower() == 'cityscapes':
        opts.num_classes = 19
    elif opts.dataset.lower() == 'camvid':
        opts.num_classes = 12
    elif opts.dataset.lower() == 'camvid_sample':
        opts.num_classes = 12
    elif opts.dataset.lower() == 'kitti_sample':
        opts.num_classes = 12
    elif opts.dataset.lower() == 'mini_city':
        opts.num_classes = 20



    # Setup visualization
    vis = Visualizer(port=opts.vis_port,
                     env=opts.vis_env) if opts.enable_vis else None
    if vis is not None:  # display options
        vis.vis_table("Options", vars(opts))

    os.environ['CUDA_VISIBLE_DEVICES'] = opts.gpu_id
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print("Device: %s" % device)

    # Setup random seed
    torch.manual_seed(opts.random_seed)
    np.random.seed(opts.random_seed)
    random.seed(opts.random_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # Setup dataloader
    if opts.dataset=='voc' and not opts.crop_val:
        opts.val_batch_size = 1

    train_dst, val_dst, test_dst = get_dataset(opts)


    train_loader = data.DataLoader(
        train_dst, batch_size=opts.batch_size, shuffle=True, num_workers=2)

    val_loader = data.DataLoader(
        val_dst, batch_size=opts.val_batch_size, shuffle=False, num_workers=2)

    test_loader = data.DataLoader(
        test_dst, batch_size=opts.val_batch_size, shuffle=False, num_workers=2)


    print("Dataset: %s, Train set: %d, Val set: %d, Test set: %d" %
          (opts.dataset, len(train_dst), len(val_dst), len(test_dst)))

    # Set up model


    model = smp.UnetPlusPlus(encoder_name="resnet50", encoder_weights="imagenet", in_channels=3, classes=12)
    # model = UNet_my_2(n_channels=3, n_classes=12, bilinear=True)
    # checkpoint = torch.load('E:/Second_paper/Checkpoint/Camvid/Blur_firstfold/main_chae/Pre_Restored/UNetmy_2_encoder_decoder_repectively/best_deeplabv3plus_resnet50_camvid_sample_os16.pth', map_location=torch.device('cuda'))
    # model.load_state_dict(checkpoint["model_state"])
    model.cuda()

    # model_enc_freeze = model.encoder()
    # checkpoint = torch.load(opts.ckpt_enc, map_location=torch.device('cpu'))
    # model_enc_freeze.load_state_dict(checkpoint["model_state"])
    # model_enc_freeze.cuda()
    # model_enc_freeze.eval()
    # for param in model_enc_freeze.parameters():
    #     param.requires_grad_(False)

    model_pre = smp.UnetPlusPlus(encoder_name="resnet50", encoder_weights="imagenet", in_channels=3, classes=12)
    checkpoint = torch.load(
        # 'E:/Second_paper/Checkpoint/Camvid/Blur_firstfold/main_chae/Pre_Restored/UNet2plusplus_pretrained_10_3_randomparam/best_deeplabv3plus_resnet50_camvid_sample_os16.pth',
        'E:/Second_paper/Checkpoint/Kitti/Segmentation/Pre_restored/psf_30_using_SDAN-MD/best_deeplabv3plus_resnet50_kitti_sample_os16.pth',
        map_location=torch.device('cuda'))
    model_pre.load_state_dict(checkpoint["model_state"])
    model_pre.cuda()
    for param in model_pre.parameters():
        param.requires_grad_(False)


    # for name, param in model.named_parameters():
    #     temp = name.find("enc")
    #     temp_2 = name.find("dec")
    #
    #     if temp==0 and temp_2 == -1:
    #         param.requires_grad=True
    #         print(f'name:{name}')
    #         print(type(param))
    #         print(f'param.shape:{param.shape}')
    #         print(f'param.requries_grad:{param.requires_grad}')
    #         print('==================================================================')
    #     else:
    #         param.requires_grad=False
    #         print(f'name:{name}')
    #         print(type(param))
    #         print(f'param.shape:{param.shape}')
    #         print(f'param.requries_grad:{param.requires_grad}')
    #         print('==================================================================')


    # Set up metrics
    metrics = StreamSegMetrics(12)

    # Set up optimizer
    # optimizer = torch.optim.SGD(params=[
    #     {'params': model.backbone.parameters(), 'lr': 0.1*opts.lr},
    #     {'params': model.classifier.parameters(), 'lr': opts.lr},
    # ], lr=opts.lr, momentum=0.9, weight_decay=opts.weight_deca
    # )

    # optimizer = torch.optim.SGD(params=[
    #     {'params': model.encoder.parameters(), 'lr': 0.1*opts.lr},
    #     {'params': model.decoder.parameters(), 'lr': opts.lr},
    #     {'params': model.segmentation_head.parameters(), 'lr': opts.lr},
    # ], lr=opts.lr, momentum=0.9, weight_decay=opts.weight_decay)

    # optimizer = optim.Adam(model.parameters(), lr=opts.lr, betas=(0.9, 0.999), eps=1e-8)
    optimizer = optim.RMSprop(model.parameters(), lr=opts.lr, weight_decay=1e-8, momentum=0.9)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'max', patience=2)  # goal: maximize Dice score

    #optimizer = torch.optim.SGD(params=model.parameters(), lr=opts.lr, momentum=0.9, weight_decay=opts.weight_decay)
    #torch.optim.lr_scheduler.StepLR(optimizer, step_size=opts.lr_decay_step, gamma=opts.lr_decay_factor)
    if opts.lr_policy=='poly':
        scheduler = utils.PolyLR(optimizer, opts.total_itrs, power=0.9)
    elif opts.lr_policy=='step':
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=opts.step_size, gamma=0.1)

    # Set up criterion
    #criterion = utils.get_loss(opts.loss_type)
    if opts.loss_type == 'focal_loss':
        criterion = utils.FocalLoss(ignore_index=255, size_average=True)
    elif opts.loss_type == 'cross_entropy':
        criterion = nn.CrossEntropyLoss(ignore_index=255, reduction='mean')
        criterion_edge_perceptual = Edge_PerceptualLoss(model_Edge, feature_extract)

    def save_ckpt(path):
        """ save current model
        """
        torch.save({
            "cur_itrs": cur_itrs,
            # "model_state": model.module.state_dict(),  ##Data.parraell 이 있으면 module 이 생긴다.
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(),
            "best_score": best_score,
        }, path)
        print("Model saved as %s" % path)



    utils.mkdir('checkpoints')
    # Restore
    best_score = 0.0
    cur_itrs = 0
    cur_epochs = 0

    total_train_miou = []
    total_train_loss = []
    total_val_miou = []
    total_val_loss = []
    # if opts.ckpt is not None and os.path.isfile(opts.ckpt):
        # del checkpoint  # free memory
    if opts.ckpt is not None and opts.test_only:
        # pass
        # https://github.com/VainF/DeepLabV3Plus-Pytorch/issues/8#issuecomment-605601402, @PytaichukBohdan

        checkpoint = torch.load(opts.ckpt, map_location=torch.device('cpu'))
        model.load_state_dict(checkpoint["model_state"])
        # print(model)
        # torch.save(model, 'E:/Second_paper/Checkpoint/Mini_City/EdgeNet/Firstfold_model/model.pt')

        # PATH_1 = 'C:/checkpoint_void/pytorch/segmentation/camvid_original_model/model.pt'
        # model = torch.load(PATH_1)
        model = nn.DataParallel(model)
        model.to(device)
        # summary(model, (3,256,256))
        # if opts.continue_training:
        #     optimizer.load_state_dict(checkpoint["optimizer_state"])
        #     scheduler.load_state_dict(checkpoint["scheduler_state"])
        #     cur_itrs = checkpoint["cur_itrs"]
        #     best_score = checkpoint['best_score']
        #     print("Training state restored from %s" % opts.ckpt)
        print("Model restored from %s" % opts.ckpt)
        # del checkpoint  # free memory
    else:
        # pass
        print("[!] Retrain")
        # model = nn.DataParallel(model)
        model.to(device)

    #==========   Train Loop   ==========#
    vis_sample_id = np.random.randint(0, len(val_loader), opts.vis_num_samples,
                                      np.int32) if opts.enable_vis else None  # sample idxs for visualization
    denorm = utils.Denormalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # denormalization for ori images

    # if opts.test_only:
    #
    #     path = 'D:/checkpoint/Segmentation/new_torch_deeplabv3plus/original'
    #     ckp_list = os.listdir(path)
    #
    #     for i in range(len(ckp_list[:-2])):
    #         test_model = model
    #
    #         ckp_name = f'_{i+1}_deeplabv3plus_resnet50_camvid_sample_os16.pth'
    #         ckp = path + '/' + ckp_name
    #         print(ckp)
    #
    #         checkpoint = torch.load(str(ckp), map_location=torch.device('cpu'))
    #         test_model.load_state_dict(checkpoint["model_state"])
    #
    #         test_model = nn.DataParallel(test_model)
    #         test_model.to(device)
    #         # print("Model restored from %s" % opts.ckpt)
    #
    #         test_model.eval()
    #         val_score, ret_samples, val_loss = val_validate(
    #             opts=opts, model=test_model, loader=val_loader, device=device, metrics=metrics, ret_samples_ids=vis_sample_id)
    #
    #         val_loss = val_loss / 350
    #         print(metrics.to_str(val_score))
    #         print(val_loss)
    #         total_val_loss.append(val_loss)
    #         total_val_miou.append(val_score['Mean IoU'])
    #
    #         val_df_train_loss = pd.DataFrame(total_val_loss)
    #         val_df_train_miou = pd.DataFrame(total_val_miou)
    #
    #         val_df_train_miou.to_csv('D:/plt/segmentation/Camvid_original/original/val_miou.csv', index=False)
    #         val_df_train_loss.to_csv('D:/plt/segmentation/Camvid_original/original/val_loss.csv', index=False)
    #
    #         # PATH = 'C:/checkpoint_void/pytorch/segmentation/camvid_original_model_2/'
    #         # torch.save(model, PATH + 'model.pt' )
    #     return

    if opts.test_only:
        model.eval()
        val_score, ret_samples = validate(
            opts=opts, model=model, loader=test_loader, device=device, metrics=metrics, ret_samples_ids=vis_sample_id)
        print(metrics.to_str(val_score))
        # PATH = 'C:/checkpoint_void/pytorch/segmentation/camvid_original_model_2/'
        # torch.save(model, PATH + 'model.pt' )

        # with torch.cuda.device(0):
        #     macs, params = get_model_complexity_info(model, (3, 240, 320), as_strings=True,
        #                                              print_per_layer_stat=True, verbose=True)
        #     print('{:<30}  {:<8}'.format('Computational complexity: ', macs))
        #     print('{:<30}  {:<8}'.format('Number of parameters: ', params))
        #     print('sdfasdfsdfdfdssfdfsfsdfafasdfsdlkfmlsdkmnflksdmfklsdmlkfsdmklfmklsdcmfgskld')
        return

    else:
        interval_loss = 0
        internval_loss_plt = 0

######### last checkpoint 받아서 이어서 학습 ##############
        # checkpoint = torch.load(
        #     f'D:/checkpoint/Segmentation/kitti/original/firstfold/_{cur_epochs + 286}_deeplabv3plus_resnet50_kitti_sample_os16.pth',
        #     map_location=torch.device('cpu'))
        # print("===>Testing using weights: ",
        #       f'D:/checkpoint/Segmentation/kitti/original/firstfold/_{cur_epochs + 286}_deeplabv3plus_resnet50_kitti_sample_os16')
        # model.load_state_dict(checkpoint["model_state"])

        # if opts.continue_training:
        #     optimizer.load_state_dict(checkpoint["optimizer_state"])
        #     scheduler.load_state_dict(checkpoint["scheduler_state"])
        #     scheduler.max_iters = opts.total_itrs
        #     cur_itrs = checkpoint["cur_itrs"]
        #     best_score = checkpoint['best_score']
        #     # print("Training state restored from %s" % opts.ckpt)
        # ######### ##############

        while True: #cur_itrs < opts.total_itrs:
            # =====  Train  =====
            # PATH_1 = 'C:/checkpoint_void/pytorch/segmentation/camvid_original_model/model.pt'
            # model = torch.load(PATH_1)
            # print(model)

            model.train()

            cur_epochs += 1

            for (images, labels) in train_loader:
                cur_itrs += 1
                images = images.to(device, dtype=torch.float32)
                labels = labels.to(device, dtype=torch.long)

                optimizer.zero_grad()
                freeze_enc_output_1, freeze_enc_output_2, freeze_enc_output_3, freeze_enc_output_4, freeze_enc_output_5, freeze_enc_output_6  = model_pre.encoder(images)
                training_enc_output_1, training_enc_output_2, training_enc_output_3, training_enc_output_4, training_enc_output_5, training_enc_output_6 = model.encoder(images)
                outputs = model(images)

                enc_feature_map_loss_1 = F.mse_loss(freeze_enc_output_1, training_enc_output_1)
                enc_feature_map_loss_2 = F.mse_loss(freeze_enc_output_2, training_enc_output_2)
                enc_feature_map_loss_3 = F.mse_loss(freeze_enc_output_3, training_enc_output_3)
                enc_feature_map_loss_4 = F.mse_loss(freeze_enc_output_4, training_enc_output_4)
                enc_feature_map_loss_5 = F.mse_loss(freeze_enc_output_5, training_enc_output_5)
                enc_feature_map_loss_6 = F.mse_loss(freeze_enc_output_6, training_enc_output_6)

                enc_featuremap_total_loss = enc_feature_map_loss_1 + enc_feature_map_loss_2 + enc_feature_map_loss_3 + enc_feature_map_loss_4 + enc_feature_map_loss_5 + enc_feature_map_loss_6
                print(enc_featuremap_total_loss)
                loss = criterion(outputs, labels) + enc_featuremap_total_loss

                # print("enc_feature_map_loss: ", enc_feature_map_loss)

###################################################################################
                pred = torch.max(outputs,1,keepdim=True)[0]
                labels = labels.to(device, dtype=torch.float32)
                labels = torch.unsqueeze(labels, 1)
                loss_perceptual = criterion_edge_perceptual(pred, labels)
                ###############################################################################
                loss = loss + 0.05 * loss_perceptual

                loss.backward()
                optimizer.step()

                np_loss = loss.detach().cpu().numpy()
                interval_loss += np_loss
                internval_loss_plt += np_loss

                if vis is not None:
                    vis.vis_scalar('Loss', cur_itrs, np_loss)

                if (cur_itrs) % 10 == 0:
                    interval_loss = interval_loss/10
                    print("Epoch %d, Itrs %d/%d, Loss=%f" %
                          (cur_epochs, cur_itrs, opts.total_itrs, interval_loss))

                    interval_loss = 0.0

                ## train loss
                if (cur_itrs) % opts.val_interval == 0:
                    internval_loss_plt = internval_loss_plt / opts.val_interval
                    print("---------Epoch %d, Itrs %d/%d, train_Loss=%f----------" %
                          (cur_epochs, cur_itrs, opts.total_itrs, internval_loss_plt))
                    total_train_loss.append(internval_loss_plt)

                ## train miou
                if (cur_itrs) % opts.val_interval == 0:
                    train_val_score, ret_samples = validate(
                        opts=opts, model=model, loader=train_loader, device=device, metrics=metrics,
                        ret_samples_ids=vis_sample_id)
                    print(train_val_score['Mean IoU'])
                    print("---------Epoch %d, Itrs %d/%d, train_Miou=%f----------" %
                          (cur_epochs, cur_itrs, opts.total_itrs, train_val_score['Mean IoU']))

                    total_train_miou.append(train_val_score['Mean IoU'])

                if (cur_itrs) % opts.val_interval == 0:
                    # save_ckpt('checkpoints/latest_%s_%s_os%d.pth' %
                    #           (opts.model, opts.dataset, opts.output_stride))
                    save_ckpt('E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Ablation/4page_not_codebook/latest_%s_%s_os%d.pth' %
                              (opts.model, opts.dataset, opts.output_stride))
                    print("validation...")
                    model.eval()
                    val_score, ret_samples = validate(
                        opts=opts, model=model, loader=test_loader, device=device, metrics=metrics, ret_samples_ids=vis_sample_id)
                    print(metrics.to_str(val_score))

                    if val_score['Mean IoU'] > best_score:  # save best model
                        best_score = val_score['Mean IoU']
                        # save_ckpt('checkpoints/best_%s_%s_os%d.pth' %
                        #           (opts.model, opts.dataset,opts.output_stride))
                        save_ckpt('E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Ablation/4page_not_codebook/best_%s_%s_os%d.pth' %
                                  (opts.model, opts.dataset, opts.output_stride))

                    if vis is not None:  # visualize validation score and samples
                        vis.vis_scalar("[Val] Overall Acc", cur_itrs, val_score['Overall Acc'])
                        vis.vis_scalar("[Val] Mean IoU", cur_itrs, val_score['Mean IoU'])
                        vis.vis_table("[Val] Class IoU", val_score['Class IoU'])

                        for k, (img, target, lbl) in enumerate(ret_samples):
                            img = (denorm(img) * 255).astype(np.uint8)
                            target = train_dst.decode_target(target).transpose(2, 0, 1).astype(np.uint8)
                            lbl = train_dst.decode_target(lbl).transpose(2, 0, 1).astype(np.uint8)
                            concat_img = np.concatenate((img, target, lbl), axis=2)  # concat along width
                            vis.vis_image('Sample %d' % k, concat_img)

                    save_ckpt('E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Ablation/4page_not_codebook/_%s_%s_%s_os%d.pth' %
                              (cur_epochs, opts.model, opts.dataset, opts.output_stride))
                    model.train()
                scheduler.step()

                if cur_itrs >= opts.total_itrs:
                    df_train_loss = pd.DataFrame(total_train_loss)
                    df_train_miou = pd.DataFrame(total_train_miou)

                    df_train_miou.to_csv('E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Ablation/4page_not_codebook/train_miou_2.csv', index=False)
                    df_train_loss.to_csv('E:/Second_paper/Checkpoint/Kitti/Segmentation/Blurred/Secondfold_5_012_random/Ablation/4page_not_codebook/train_loss_2.csv', index=False)


                    # plt.plot(total_train_miou)
                    # plt.xlabel('epoch')
                    # plt.ylabel('miou')
                    plt.rcParams['axes.xmargin'] = 0
                    plt.rcParams['axes.ymargin'] = 0
                    plt.plot(total_train_miou)
                    plt.xlabel('epoch')
                    plt.ylabel('miou')
                    plt.show()

                    # plt.rcParams['axes.xmargin'] = 0
                    # plt.rcParams['axes.ymargin'] = 0
                    plt.plot(total_train_loss)
                    plt.xlabel('epoch')
                    plt.ylabel('loss')
                    plt.show()

                    return

        # df_train_loss = pd.DataFrame(total_train_loss)
        # df_train_miou = pd.DataFrame(total_train_miou)
        #
        # df_train_miou.to_csv('D:/plt/segmentation/KITTI/original/train_miou.csv', index=False)
        # df_train_loss.to_csv('D:/plt/segmentation/KITTI/original/train_loss.csv', index=False)
        #
        # plt.plot(cur_epochs, total_train_miou)
        # plt.xlabel('epoch')
        # plt.ylabel('miou')
        # plt.rcParams['axes.xmargin'] = 0
        # plt.rcParams['axes.ymargin'] = 0
        # plt.show()
        #
        # plt.plot(cur_epochs, total_train_loss)
        # plt.xlabel('epoch')
        # plt.ylabel('loss')
        # plt.rcParams['axes.xmargin'] = 0
        # plt.rcParams['axes.ymargin'] = 0
        # plt.show()


if __name__ == '__main__':
    main()
