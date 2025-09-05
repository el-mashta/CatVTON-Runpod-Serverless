[](https://openreview.net/group?id=ICLR.cc/2025/Conference "Venue Homepage")

## CatVTON: Concatenation Is All You Need for Virtual Try-On with Diffusion Models

[![Download PDF](https://openreview.net/images/pdf_icon_blue.svg)](https://openreview.net/pdf?id=jt1h2dnmng "Download PDF")

### [Zheng Chong](https://openreview.net/profile?id=~Zheng_Chong1), [Xiao Dong](https://openreview.net/profile?id=~Xiao_Dong1), [Haoxiang Li](https://openreview.net/profile?id=~Haoxiang_Li1), [shiyue Zhang](https://openreview.net/profile?id=~shiyue_Zhang2), [Wenqing Zhang](https://openreview.net/profile?id=~Wenqing_Zhang2), [Hanqing Zhao](https://openreview.net/profile?id=~Hanqing_Zhao4), [xujie zhang](https://openreview.net/profile?id=~xujie_zhang1), [Dongmei Jiang](https://openreview.net/profile?id=~Dongmei_Jiang2), [Xiaodan Liang](https://openreview.net/profile?id=~Xiaodan_Liang2)

Published: 22 Jan 2025, Last Modified: 28 Feb 2025ICLR 2025 PosterEveryone[Revisions](https://openreview.net/revisions?id=jt1h2dnmng)[BibTeX](https://openreview.net/forum?id=jt1h2dnmng#)[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

**Keywords:** diffusion models, virtual try-on, parameter-efficient training

**TL;DR:** A high-quality virtual try-on diffusion model with parameter efficiency and simplified inference.

**Abstract:**

Virtual try-on methods based on diffusion models achieve realistic effects but often require additional encoding modules, a large number of training parameters, and complex preprocessing, which increases the burden on training and inference. In this work, we re-evaluate the necessity of additional modules and analyze how to improve training efficiency and reduce redundant steps in the inference process. Based on these insights, we propose CatVTON, a simple and efficient virtual try-on diffusion model that transfers in-shop or worn garments of arbitrary categories to target individuals by concatenating them along spatial dimensions as inputs of the diffusion model. The efficiency of CatVTON is reflected in three aspects: (1) Lightweight network. CatVTON consists only of a VAE and a simplified denoising UNet, removing redundant image and text encoders as well as cross-attentions, and includes just 899.06M parameters. (2) Parameter-efficient training. Through experimental analysis, we identify self-attention modules as crucial for adapting pre-trained diffusion models to the virtual try-on task, enabling high-quality results with only 49.57M training parameters. (3) Simplified inference. CatVTON eliminates unnecessary preprocessing, such as pose estimation, human parsing, and captioning, requiring only a person image and garment reference to guide the virtual try-on process, reducing over 49% memory usage compared to other diffusion-based methods. Extensive experiments demonstrate that CatVTON achieves superior qualitative and quantitative results compared to baseline methods and demonstrates strong generalization performance in in-the-wild scenarios, despite being trained solely on public datasets with 73K samples.

**Primary Area:** generative models

**Code Of Ethics:** I acknowledge that I and all co-authors of this work have read and commit to adhering to the ICLR Code of Ethics.

**Submission Guidelines:** I certify that this submission complies with the submission instructions as described on [https://iclr.cc/Conferences/2025/AuthorGuide](https://iclr.cc/Conferences/2025/AuthorGuide).

**Anonymous Url:** I certify that there is no URL (e.g., github page) that could be used to find authors’ identity.

**No Acknowledgement Section:** I certify that there is no acknowledgement section in this submission for double blind review.

**Submission Number:** 833

Filter by reply type...

Filter by author...

Sort: Newest FirstSort: Oldest First

![back arrow](https://openreview.net/images/linear_icon.svg "Linear discussion layout")Linear![back arrow](https://openreview.net/images/threaded_icon.svg "Threaded discussion layout")Threaded![back arrow](https://openreview.net/images/nested_icon.svg "Nested discussion layout")Nested

−Collapsed＝Default≡Expanded

Copy link

 Everyone

_12 / 12 replies shown_

Add:Public Comment

−＝≡

#### **Paper Decision**

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=ROdddAjP8N)

Decisionby Program Chairs22 Jan 2025, 00:23 (modified: 11 Feb 2025, 02:22)Everyone[Revisions](https://openreview.net/revisions?id=ROdddAjP8N)

**Decision:** Accept (Poster)

Add:Public Comment

−＝≡

#### Meta Review of Submission833 by Area Chair pojz

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=QNIqmBG0TZ)

Meta Reviewby Area Chair pojz15 Dec 2024, 13:05 (modified: 05 Feb 2025, 00:13)Everyone[Revisions](https://openreview.net/revisions?id=QNIqmBG0TZ)

**Metareview:**

In this paper, the authors propose CatVTON, a simple and efficient virtual try-on diffusion model using a VAE and denoising UNet with spatial concatenation, reducing memory usage and training parameters. The paper demonstrated competitive performance on standard benchmarks and in real-world scenarios, with strong generalization and efficient inference. However, the reviewers raised concerns about reproducibility due to discrepancies in evaluation metrics compared to prior works, insufficient explanation of the concatenation's advantages, and a lack of detailed theoretical validation.

After the author-reviewer discussion period, most of the reviewers confirmed their concerns had been addressed. However, Reviewer iWwH still has two important remaining concerns:

-   Discrepancies in quantitative results: there are significant discrepancies between the reported results in the submission and the original baseline papers.
-   Architectural and textual inconsistencies: there is a minor but important inconsistency between the overall architecture figure and the description in the main text.

Considering most of the reviewers are positive towards this submission, and Reviewer iWwH is not strongly against accepting it, I recommend acceptance. However, the discussions between the reviewers and authors, especially the concerns from Reviewer iWwH, should be included in the final version.

**Additional Comments On Reviewer Discussion:**

During the author-reviewer discussion period, most of the reviewers confirmed their concerns had been addressed. However, Reviewer iWwH still has two important remaining concerns:

-   Discrepancies in quantitative results: there are significant discrepancies between the reported results in the submission and the original baseline papers.
-   Architectural and textual inconsistencies: there is a minor but important inconsistency between the overall architecture figure and the description in the main text.

Considering most of the reviewers are positive towards this submission, and Reviewer iWwH is not strongly against accepting it, I recommend acceptance. However, the discussions between the reviewers and authors, especially the concerns from Reviewer iWwH, should be included in the final version.

Add:Public Comment

−＝≡

#### Official Review of Submission833 by Reviewer mw7R

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=yGxtIGxFdO)

Official Reviewby Reviewer mw7R03 Nov 2024, 22:37 (modified: 12 Nov 2024, 11:02)Everyone[Revisions](https://openreview.net/revisions?id=yGxtIGxFdO)

**Summary:**

The study re-evaluates the necessity of additional modules in virtual try-on methods based on diffusion models and proposes CatVTON, a simple and efficient model. CatVTON transfers garments of arbitrary categories to target individuals by concatenating them as inputs, removing redundant encoding modules and steps. It features a lightweight network with just 899.06M parameters, efficient training with only 49.57M parameters through self-attention modules, and simplified inference that requires only person image and garment reference, reducing memory usage by 49%+. Experiments show that CatVTON achieves superior results and generalizes well in real-world scenarios, despite being trained on a limited public dataset.

**Soundness:** 3: good

**Presentation:** 3: good

**Contribution:** 2: fair

**Strengths:**

-   1.  This paper proposes CatVTON, a lightweight virtual try-on diffusion model with only 899.06M parameters, that achieves high-quality results by simply concatenating garment and person images as inputs, eliminating the need for extra image encoders, ReferenceNet, and text-conditioned modules.
-   2.  This paper introduces a parameter-efficient training strategy to transfer pre-trained diffusion models to virtual try-on tasks while preserving prior knowledge by training necessary modules with only 49.57M parameters
-   3.  This paper simplifies the inference process by eliminating the need for extra pre-processing of input images and leveraging the robust priors from pre-trained diffusion models to infer all necessary information, reducing memory usage by 49%+ compared to other diffusion-based baselines

**Weaknesses:**

-   1.  The effectiveness of the try-on process relies on the accuracy of the provided masks; inaccurate masks may significantly degrade the quality of the results. When the authors conducted mask-free experiments, how did they ensure that the model paid attention to the try-on areas?
-   2.  Some of the data in Table 1 seem to differ from those in the original paper, why?
-   3.  Based on Table 3, it seems that choosing to train either the Unet or Transformers module can achieve better results, albeit with higher memory demands and slower training. How to balance this relationship?
-   4.  Please provide the training code to demonstrate reproducibility.
-   5.  The method is simple and effective, however, the entire process is overly engineered, lacking rigorous theoretical validation and support in a conference like ICLR.

**Questions:**

Please refer to "Weaknesses."

**Flag For Ethics Review:** No ethics review needed.

**Rating:** 6: marginally above the acceptance threshold

**Confidence:** 5: You are absolutely certain about your assessment. You are very familiar with the related work and checked the math/other details carefully.

**Code Of Conduct:** Yes

Add:Public Comment

−＝≡

#### Official Comment by Authors

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=jcEnRSDQ9C)

Official Commentby Authors25 Nov 2024, 03:27Everyone

**Comment:**

We hope our response has addressed your concerns. If there are any other issues you'd like to discuss, please don't hesitate to let us know.

Add:Public Comment

−＝≡

##### Replying to Official Comment by Authors

#### Official Comment by Reviewer mw7R

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=jQ9jgIFqlT)

Official Commentby Reviewer mw7R25 Nov 2024, 10:46Everyone

**Comment:**

The author has addressed my main concerns, so I don't have any further questions.

Add:Public Comment

−＝≡

#### Official Review of Submission833 by Reviewer oVwb

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=UWiSHK6gzA)

Official Reviewby Reviewer oVwb03 Nov 2024, 02:54 (modified: 26 Nov 2024, 04:05)Everyone[Revisions](https://openreview.net/revisions?id=UWiSHK6gzA)

**Summary:**

CatVTON is a virtual try-on model that achieves high-quality and efficient garment transfer without relying on additional encoders or complex preprocessing. Unlike traditional virtual try-on approaches, CatVTON simplifies the architecture by using only a VAE and a single, lightweight UNet with a self-attention module, reducing the parameter count to 899.06M. Moreover, this model directly concatenates the person and garment images along spatial dimensions, requiring only 49.57M trainable parameters and cutting down inference memory usage by over 49% compared to other methods. Extensive experiments demonstrate that CatVTON achieves superior results in both controlled and in-the-wild settings.

**Soundness:** 3: good

**Presentation:** 3: good

**Contribution:** 3: good

**Strengths:**

-   CatVTON proposes a lightweight architecture, which highly reduces computational cost during the model training. Meanwhile, it only requires 49.57M training parameters.
    
-   The model generalises well in diverse real-world scenarios, performing effectively even with limited training data.
    
-   CatVTON is able to achieve realistic try-on results with accurate garment alignment and detail preservation.
    

**Weaknesses:**

-   While the authors present CatVTON as a lightweight virtual try-on diffusion model and it only requires very few training parameters, it would be beneficial to include results on inference speed and computational cost. Additionally, demonstrating the model’s deployability on embedded devices could enhance understanding of its practical applications.
    
-   The mask-free model is derived from a trained mask-based model. It would be better to discuss potential error accumulation in this transition.
    
-   CatVTON introduces a model design and training strategy aimed at creating a lightweight model with fewer training parameters. It would be useful to consider whether this approach could be extended to other virtual try-on pipelines, particularly non-diffusion-based methods.
    

**Questions:**

-   Can you provide additional quantitative results on CatVTON’s inference speed and computational cost, and is the model deployable on embedded or resource-constrained devices?
    
-   Given that the mask-free model builds on a trained mask-based model, have you observed any error accumulation in this process, and if so, what techniques might mitigate such errors?
    
-   Could the lightweight model design and parameter-efficient training strategy you propose for CatVTON be applicable to other virtual try-on frameworks, including non-diffusion-based methods?
    

**Flag For Ethics Review:** No ethics review needed.

**Rating:** 6: marginally above the acceptance threshold

**Confidence:** 4: You are confident in your assessment, but not absolutely certain. It is unlikely, but not impossible, that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work.

**Code Of Conduct:** Yes

Add:Public Comment

−＝≡

#### Official Comment by Authors

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=yyCX5xxgIK)

Official Commentby Authors25 Nov 2024, 03:27Everyone

**Comment:**

We hope our response has addressed your concerns. If there are any other issues you'd like to discuss, please don't hesitate to let us know.

Add:Public Comment

−＝≡

#### Official Review of Submission833 by Reviewer F9hE

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=YM5ETXpidM)

Official Reviewby Reviewer F9hE28 Oct 2024, 03:57 (modified: 12 Nov 2024, 11:02)Everyone[Revisions](https://openreview.net/revisions?id=YM5ETXpidM)

**Summary:**

This paper aims to efficiently adapt pre-trained diffusion models to high-quality virtual try-on. It introduces efficiency improvements in three key areas: model architecture, parameter-efficient training, and simplified inference, and analyzes the motivation and feasibility from the perspective of image representation interaction, supported by experimental validation. Extensive qualitative and quantitative experiments are conducted on VITON-HD and DressCode datasets, along with ablation studies on key components of proposed method. Compared to other virtual try-on methods, this method demonstrates significant advantages in model parameters, training efficiency, and inference costs while achieving better performance. Despite being trained on small-scale public datasets, results and comparisons in in-the-wild scenarios demonstrate the method's generalization capabilities.

**Soundness:** 4: excellent

**Presentation:** 4: excellent

**Contribution:** 4: excellent

**Strengths:**

1.  Originality: This paper focuses on efficiency optimizations in diffusion models for virtual try-on. By simplifying the model architecture with a concatenation operation and identifying key modules through an analysis of image representation interactions, it achieves parameter-efficient training. Additionally, by streamlining preprocessing in inference, it achieves efficient inference without extra conditions. The approach and model architecture differ significantly from other virtual try-on models, addressing the efficiency issues of previous work. The paper offers new insights into the application of image representation interactions in generative models, demonstrating innovation.
    
2.  Quality: This paper conducts extensive comparative and ablation experiments to validate its performance. Qualitative and quantitative analyses are provided on two major open-source datasets, DressCode and VITON-HD, in comparison with recent virtual try-on methods. Quantitatively, the proposed model shows significant advantages in model size, trainable parameters, and inference memory usage, while surpassing other methods in FID, KID, SSIM, and LPIPS metrics. Visually, the model generates highly realistic details such as text logos and patterns, and performs well in in-the-wild virtual try-on scenarios.
    
3.  Clarity: The writing is well-structured, with a clear and logical flow of content. Plenty of figures, tables, and formulas are used to explain and analyze key insights and experimental details. The writing is smooth, with no obvious grammatical errors or inconsistencies.
    
4.  Significance: This work offers insights and contributions to the application of diffusion models in virtual try-on tasks. Its lightweight architecture and parameter-efficient training significantly reduce model training costs and may be transferable to other downstream tasks. The model's low memory usage during inference and simplified inference process reduce hardware requirements, making it more cost-effective to deploy.
    

**Weaknesses:**

1.  The description of the proposed mask-free training method is not specific and detailed enough, more information should be provided such as the dataset details used for this part of the training and the exact process of pseudo-data construction.
    
2.  The Concatenation operation applied to garment and person features lacks a more explicit and detailed discussion, such as its advantages over encoder features like CLIP or DINO.
    
3.  The transferability of the proposed efficient virtual try-on method based on Stable Diffusion is not discussed. For example, migrating this training framework to more advanced image generation diffusion models, such as DiT, to verify the generality of this framework.
    
4.  Some inappropriate formatting issues, such as inconsistent font sizes in tables. The font in Table 1 and Table 4 is relatively small, and there is excessive whitespace in Table 4. The images in Figure 5 and Figure 6, which are used to display generated results, are arranged too tightly.
    

**Questions:**

1.  Can the proposed efficient training method be transferred to other more novel diffusion models, such as DiT?
    
2.  Will the generated dataset used for mask-free training be open-sourced to support future research?
    
3.  Provide more details about Mask-free training, such as dataset construction and how it differs from Mask-based model training, visual comparison of its results with Mask-based model results, etc.
    
4.  Adjust the layout of the tables and figures to make them more uniform and standardized.
    

**Flag For Ethics Review:** No ethics review needed.

**Rating:** 8: accept, good paper

**Confidence:** 5: You are absolutely certain about your assessment. You are very familiar with the related work and checked the math/other details carefully.

**Code Of Conduct:** Yes

Add:Public Comment

−＝≡

#### Official Comment by Reviewer F9hE

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=fifxC2il07)

Official Commentby Reviewer F9hE24 Nov 2024, 21:10Everyone

**Comment:**

Thanks for the author's reply. The author's reply answered my doubts.

Add:Public Comment

−＝≡

##### Replying to Official Comment by Reviewer F9hE

#### Official Comment by Authors

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=Ut9Y3wIWIZ)

Official Commentby Authors25 Nov 2024, 03:26Everyone

**Comment:**

Thank you for your feedback. We're glad our response addressed your concerns.

Add:Public Comment

−＝≡

#### Official Review of Submission833 by Reviewer iWwH

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=MrzLWiIz3k)

Official Reviewby Reviewer iWwH27 Oct 2024, 14:43 (modified: 09 Dec 2024, 00:32)Everyone[Revisions](https://openreview.net/revisions?id=MrzLWiIz3k)

**Summary:**

**Post-discussion period**

* * *

I will maintain my current score of 5, as the issues I raised in my review remain unresolved:

-   Discrepancies in Quantitative Results: There are significant discrepancies between the reported results in the submission and the original baseline papers. This inconsistency makes the comparison less convincing. To address this, I suggested that the authors use the original evaluation scripts from the baseline papers alongside their own settings, but it is disregarded. This would provide a fairer comparison, particularly given the considerable variance observed in metrics like LPIPS, FID, and KID.
    
-   Architectural and Textual Inconsistencies: There is a minor but important inconsistency between the overall architecture figure and the description in the main text. Specifically, the process of input concatenation, whether in pixel-space or latent-space, is unclear. This discrepancy raises questions about whether the results are indeed identical to what was claimed.
    

For me, if there are unclear aspects in a submission and the authors disregard suggestions such as using original scripts for reevaluation, I cannot raise the score or recommend acceptance unless these concerns are fully addressed. The final decision I would let the effort of ACs.

* * *

This work introduces CatVTON, a diffusion-based virtual try-on model that enhances efficiency by removing complex modules and preprocessing steps typical in other approaches. Diffusion-based virtual try-on methods usually require additional encoding, extensive training, and preprocessing, which CatVTON addresses by simplifying the architecture to a VAE and denoising UNet, reducing parameters to 899.06M. Through analysis, the authors find that self-attention modules are essential for adapting diffusion models to this task, enabling high-quality outputs with only 49.57M training parameters. CatVTON further reduces inference complexity, eliminating pre-processings like pose estimation and human parsing, which cuts memory usage by over 49%. Extensive testing demonstrates CatVTON’s strong performance and generalization, even with a limited 73K sample dataset, achieving better results than baseline methods in both controlled and real-world scenarios. Experiments are conducted on two datasets: VITON-HD and DressCode.

**Soundness:** 2: fair

**Presentation:** 2: fair

**Contribution:** 3: good

**Strengths:**

-   Removing the redundant reference Unet of most existing work is a good direction as it makes the model lightweight and simplified.
-   Results on two benchmark datasets VTON-HD and DressCode show good performance.

**Weaknesses:**

**Concerns**

-   Inference speed comparison is missing since the proposed model is more lightweight, it is more beneficial to see this metric.
    
-   Many works (AnyDoor, MimicBrush, Uni-ControlNet) show that a strong pre-trained image encoder (CLIP, DINOv2, Unet) would provide more priors and good features for better imager generation with better details, but this work shows that removing all of them, and using only VAE outputs can give even better performance. Which in my opinion, it might not be very reasonable. A valid explanation is needed to this point and also I believe that whether the code of this paper is publicly available for the community to verify its validity and reproducibility is crucial.
    
-   The detail of all numeric numbers in Table 1, and Table 2 should be clarified. Were all of them reproduced by the author or were they quoted from somewhere else? Looking at the original papers (OOTDiffusion and others) I find that they report much higher numbers compared to the numbers shown in this submission. It raised questions about the correctness and what made the differences since they used also the same dataset.
    
-   "DREAM \\lambda", just putting this terminology here is not very informative, it is quite hard to understand what is that parameter \\lambda and what is DREAM here without some more detailed explanations.
    

For the whole paper, the current form seems to use all \\cite{} making it very messy for all references. I think the use of \\citep{} in latex would produce a more correct presentation of citations for many parts of the paper. Using \\cite{} for cases where the citing author is subject (S), but \\citep{} for other cases when referring to the paper.

\[1\] AnyDoor: Zero-shot Object-level Image Customization, CVPR 2024

\[2\] MimicBrush: Zero-shot Image Editing with Reference Imitation, arXiv:2406.07547

\[3\] Uni-ControlNet: All-in-One Control to Text-to-Image Diffusion Models, EnruIPS 2023

**Questions:**

Q1. What is the IPS metric? It is better to provide its definition and description of it if it is newly proposed or referred to if needed.

**Flag For Ethics Review:** No ethics review needed.

**Rating:** 5: marginally below the acceptance threshold

**Confidence:** 4: You are confident in your assessment, but not absolutely certain. It is unlikely, but not impossible, that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work.

**Code Of Conduct:** Yes

Add:Public Comment

−＝≡

#### Official Comment by Authors

[](https://openreview.net/forum?id=jt1h2dnmng¬eId=XbnsJTPRQo)

Official Commentby Authors25 Nov 2024, 03:26Everyone

**Comment:**

We hope our response has addressed your concerns. If there are any other issues you'd like to discuss, please don't hesitate to let us know.