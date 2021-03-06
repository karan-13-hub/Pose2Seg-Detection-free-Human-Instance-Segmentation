import numpy as np
import cv2
import math

##########################################################################################################
# load heatmap and paf
def genHeatmaps(kpts, height, width, stride, sigma, visdiff=False):
    threshold = 4.6025 * sigma ** 2 * 2
    start = stride / 2 - 0.5
    h, w = height // stride, width // stride
    sqrt_threshold = math.sqrt(threshold)

    hms = np.zeros((h, w, kpts.shape[1]))
    for k in range(kpts.shape[1]):
        hm = hms[:, :, k]
        points = kpts[:, k, :]
        for x_center, y_center, vis in points:
            if vis == 0:
                continue

            x_min, y_min = [max(0, int((p - sqrt_threshold - start) / stride)) for p in (x_center, y_center)]
            x_max, y_max = [min(l - 1, int((p + sqrt_threshold - start) / stride)) for (l, p) in zip((w, h), (x_center, y_center))]
            xs = np.arange(x_min, x_max + 1)
            ys = np.arange(y_min, y_max + 1)[:, np.newaxis]
            xs, ys = [start + p * stride for p in (xs, ys)]
            d2 = ((xs - x_center) ** 2 + (ys - y_center) ** 2) / 2 / sigma ** 2
            idxs = np.where(d2 < 4.6025)

            region = hm[y_min:(y_max + 1), x_min:(x_max + 1)][idxs]
            region = np.max(np.stack((region, np.exp(-d2[idxs]))), axis=0)
            if visdiff==True and vis==1: # not visible for coco.
                region *= -1
            hm[y_min:(y_max + 1), x_min:(x_max + 1)][idxs] = region

    return hms

def showAnns(img, keypoints, BODY_PARTS):
    img = img.copy()
    for i in range(len(keypoints)):
        kpt = np.array(keypoints[i]).reshape(-1, 3)
        
        for j in range(kpt.shape[0]):
            x = kpt[j][0]
            y = kpt[j][1]
            cv2.circle(img, (int(x), int(y)), 8, colors[i], -1) # draw points
        
        for part in BODY_PARTS:
                         # Connect via body_part_m
                         # The part is the node coordinate of part[0], here we need to subtract 1. Because the result obtained starts with 0, and the provided one starts with 1.
            keypoint_1 = kpt[part[0] - 1] 
            x_1 = int(keypoint_1[0]) # coordinate of a single part x
            y_1 = int(keypoint_1[1])
            keypoint_2 = kpt[part[1] - 1]
            x_2 = int(keypoint_2[0])
            y_2 = int(keypoint_2[1])
            if keypoint_1[2] > 0 and keypoint_2[2] > 0:
                cv2.line(img, (x_1, y_1), (x_2, y_2), colors[i], 3)
    cv2.imshow('keypoints', img)
    cv2.waitKey(20000)

def genSkeletons(kpts, height, width, stride, sigma, threshold, visdiff=False):
    conns = ((0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 6), (5, 7), (5, 11), (6, 8),
            (6, 12), (7, 9), (8, 10), (11, 12), (11, 13), (12, 14), (13, 15), (14, 16))
    # vis: kpts[:, :, 2]. for coco, 2 is visible, 1 is not visible, 0 is missing.
    Pafs = genPafs(kpts, conns, height, width, stride, threshold)
    Heatmaps = genHeatmaps(kpts, height, width, stride, sigma, visdiff)
    # print("Heatmaps",Heatmaps)
    # print("Pafs: ",Pafs)
    return np.concatenate((Heatmaps, Pafs), axis=2)

def genPafs(kpts, conns, height, width, stride, threshold):
    h, w = height // stride, width // stride

    pafs = np.zeros((h, w, len(conns) * 2))
    for (k, conn) in enumerate(conns):
        pafa = pafs[:, :, k * 2]
        pafb = pafs[:, :, k * 2 + 1]
        points1 = kpts[:, conn[0], :]
        points2 = kpts[:, conn[1], :]

        for ((x_center1, y_center1, vis1), (x_center2, y_center2, vis2)) in zip(points1, points2):
            if vis1 == 0 or vis2 == 0:
                continue
            x_center1, y_center1, x_center2, y_center2 = [s / stride for s in (x_center1, y_center1, x_center2, y_center2)]
            line = np.array((x_center2 - x_center1, y_center2 - y_center1))
            if np.linalg.norm(line) == 0:
                continue
            x_max = min(int(round(max(x_center1, x_center2) + threshold)), w)
            y_max = min(int(round(max(y_center1, y_center2) + threshold)), h)
            x_min = max(int(round(min(x_center1, x_center2) - threshold)), 0)
            y_min = max(int(round(min(y_center1, y_center2) - threshold)), 0)

            line /= np.linalg.norm(line)
            vx, vy = [paf[y_min:y_max, x_min:x_max] for paf in (pafa, pafb)]
            xs = np.arange(x_min, x_max)
            ys = np.arange(y_min, y_max)[:, np.newaxis]

            v0, v1 = xs - x_center1, ys - y_center1
            dist = abs(v0 * line[1] - v1 * line[0])
            idxs = dist < threshold

            pafa[y_min:y_max, x_min:x_max][idxs] = line[0]
            pafb[y_min:y_max, x_min:x_max][idxs] = line[1]

    return pafs
