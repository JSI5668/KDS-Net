import scipy.stats
import numpy as np

# ## Kitti performance #############################################################################################
#
# proposed_method = [56.52, 54.65]
# second_best_method = [53.72, 53.91]
# # third_best_method = [0.12, 0.46]
#
# lresult = scipy.stats.levene(proposed_method, second_best_method)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult))
# m_miou = scipy.stats.ttest_ind(proposed_method, second_best_method, equal_var=False)
# print("m_miou", m_miou)
# # m_miou_rel = scipy.stats.ttest_rel(proposed_method, second_best_method)
# # print("m_miou_rel", m_miou_rel)
# print('#############################################################################################')
# ########################################################################
#
# proposed_method_overall_acc = [87.51, 87.03]
# second_best_method_overall_acc = [86.70, 87.01]
# # third_best_method = [0.12, 0.46]
#
# lresult_overall_acc = scipy.stats.levene(proposed_method_overall_acc, second_best_method_overall_acc)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult_overall_acc))
# m_overall_acc = scipy.stats.ttest_ind(proposed_method_overall_acc, second_best_method_overall_acc, equal_var=False)
# print("m_overall_acc", m_overall_acc)
# # m_overall_acc_rel = scipy.stats.ttest_rel(proposed_method_overall_acc, second_best_method_overall_acc)
# # print("m_overall_acc_rel", m_overall_acc_rel)
# print('#############################################################################################')
# ########################################################################
#
# proposed_method_mean_acc = [64.97, 62.15]
# second_best_method_mean_acc = [61.78, 62.31]
# #
# lresult_mean_acc = scipy.stats.levene(proposed_method_mean_acc, second_best_method_mean_acc)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult_mean_acc))
# m_mean_acc = scipy.stats.ttest_ind(proposed_method_mean_acc, second_best_method_mean_acc, equal_var=False)
# print("m_mean_acc", m_mean_acc)
# # m_mean_acc_rel = scipy.stats.ttest_rel(proposed_method_mean_acc, second_best_method_mean_acc)
# # print("m_overall_acc_rel", m_mean_acc_rel)
# print('#############################################################################################')
# ########################################################################
#
# proposed_method_Freq_iou = [78.31, 77.37]
# second_best_method_Freq_iou = [77.08, 77.30]
# # third_best_method = [0.12, 0.46]
#
# m_Freq_iou = scipy.stats.ttest_ind(proposed_method_Freq_iou, second_best_method_Freq_iou, equal_var=False)
# print("m_Freq_iou", m_Freq_iou)
# print('#############################################################################################')
#


## Camvid performance #############################################################################################

# proposed_method = [72.31, 72.52]
# second_best_method = [69.48, 69.68]
## KITTI performance #############################################################################################
proposed_method = [59.31, 59.27]
second_best_method = [56.52, 54.65]

##독립표본
# lresult = scipy.stats.levene(proposed_method, second_best_method)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult))
# m_miou = scipy.stats.ttest_ind(proposed_method, second_best_method, equal_var=False)
# print("m_miou", m_miou)

##대응표본 이걸로 하는게 맞고, metrics 가 클수록 좋은거면 greater, 작을수록 좋은거면 less, 절대값이 클수록 좋은거면 two-sided
m_miou_rel = scipy.stats.ttest_rel(proposed_method, second_best_method, alternative='greater')
print("m_miou_rel", m_miou_rel)
print('#############################################################################################')

## Camvid performance #############################################################################################
# proposed_method_overall_acc = [93.67, 93.70]
# second_best_method_overall_acc = [92.84, 92.94]
## KITTI performance #############################################################################################
proposed_method_overall_acc = [90.22, 89.98]
second_best_method_overall_acc = [87.51, 87.03]

# lresult_overall_acc = scipy.stats.levene(proposed_method_overall_acc, second_best_method_overall_acc)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult_overall_acc))
# m_overall_acc = scipy.stats.ttest_ind(proposed_method_overall_acc, second_best_method_overall_acc, equal_var=False)
# print("m_overall_acc", m_overall_acc)
m_overall_acc_rel = scipy.stats.ttest_rel(proposed_method_overall_acc, second_best_method_overall_acc, alternative='greater')
print("m_overall_acc_rel", m_overall_acc_rel)
print('#############################################################################################')
########################################################################
## Camvid performance #############################################################################################
# proposed_method_mean_acc = [79.57, 80.03]
# second_best_method_mean_acc = [76.67, 76.96]
## KITTI performance #############################################################################################
proposed_method_mean_acc = [66.50, 66.71]
second_best_method_mean_acc = [64.96, 62.15]

# lresult_mean_acc = scipy.stats.levene(proposed_method_mean_acc, second_best_method_mean_acc)
# print('LeveneResult(F) : %.3f \np-value : %.3f' % (lresult_mean_acc))
# m_mean_acc = scipy.stats.ttest_ind(proposed_method_mean_acc, second_best_method_mean_acc, equal_var=False)
# print("m_mean_acc", m_mean_acc)
m_mean_acc_rel = scipy.stats.ttest_rel(proposed_method_mean_acc, second_best_method_mean_acc, alternative='greater')
print("m_mean_acc_rel", m_mean_acc_rel)
print('#############################################################################################')
########################################################################
## Camvid performance #############################################################################################
# proposed_method_Freq_iou = [88.52, 88.60]
# second_best_method_Freq_iou = [87.04, 87.17]
## KITTI performance #############################################################################################
proposed_method_Freq_iou = [82.59, 82.12]
second_best_method_Freq_iou = [78.31, 77.37]
# m_Freq_iou = scipy.stats.ttest_ind(proposed_method_Freq_iou, second_best_method_Freq_iou, equal_var=False)
# print("m_Freq_iou", m_Freq_iou)
m_Freq_iou_rel = scipy.stats.ttest_rel(proposed_method_Freq_iou, second_best_method_Freq_iou, alternative='greater')
print("m_Freq_iou_rel", m_Freq_iou_rel)
print('#############################################################################################')

##cohen's d value
## MIoU
t = m_miou_rel.statistic
df = len(proposed_method) + len(second_best_method) - 2
print(abs(t) / np.sqrt(df)), print("d-value of m_miou")

## Pixel Acc
t_pixel_acc = m_overall_acc_rel.statistic
df = len(proposed_method_overall_acc) + len(second_best_method_overall_acc) - 2
print(abs(t_pixel_acc) / np.sqrt(df)), print("d-value of m_pixel_acc")

## Pixel mean Acc
t_pixel_mean_acc = m_mean_acc_rel.statistic
df = len(proposed_method_mean_acc) + len(second_best_method_mean_acc) - 2
print(abs(t_pixel_mean_acc) / np.sqrt(df)), print("d-value of m_mean_acc")

## Pixel frequency iou
t_frequency_iou = m_Freq_iou_rel.statistic
df = len(proposed_method_Freq_iou) + len(second_best_method_Freq_iou) - 2
print(abs(t_frequency_iou) / np.sqrt(df)), print("d-value of m_frequency_iou")