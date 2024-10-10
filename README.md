# DocSegment 
docx文本语义切分（知识库领域）

该切分方法暂时仅适用于严格按照切分office word样式进行标题分层的文档。

## 字符过滤
该方法仅过滤`<p href=>`等类似的html标识

## 章节拆分
按照office word样式对文章拆分，拆分成小节内容，为每个小节内容添加元数据

## 语义切分
在完成章节拆分后获取每个完整内容块，考虑到即使是同一标题下的内容，如果不切分存储，面临以下问题：
1. 可能会造成知识库检索困难
2. 从知识库中找到相关本文，塞入prompt中，导致prompt过长
3. 可能导致回答不准确，LLM对长文本理解存在lost in middle<sup>[1-3]</sup>，只对文本前后内容较为敏感

基于以上内容和部分模型的性能，需要对知识库内容切片。

### 相关研究
从文章<sup>[1]</sup>中将文本的`chunk`切分方式为如下4中类型：
* fixed-size: 固定大小/长度
* sentence: 按照句子切分
* semantic：语义切分
* special：包括对html,md,json的切分

从知识库角度，文本的切分粒度由检索方式决定。从检索的视角上来看，从小到大的粒度为: `Token`,`Phrase`,`Sentence`,`Proposition`,`Chunk`
在DenseX模型中，尝试将文本切分为更为精准的`Proposition`，作为一种原子表达(atomic expressions)。
大部分的切分采用`chunk`——一组包含相同语义的`Token`。也存在检索的时候并没有对文档切分，而是采用了更复杂的检索策略，此处不额外延伸


### 切分策略
语义切分，尝试将相同的句子聚集在一起，形成一个chunk，以下为切分一个chunk的简单示例：
```text
while(i+j<len(sentences) and embed(sentences[i:i+j])- embed(sentences[i:i+j+1]) > threshold):
    j++
chunk = sentences[i:i+j]
```
理论上，需要从开始位置找到，记录从每加入下一句话后，与未加入这句话的相似度，如果相似度相差较大，表面在当前新加入的句子之前作为一个`chunk`。
在实际执行中，由于当前待确认的`chunk`会持续累加句子，embedding模型在向量化时，相同的句子的比例会越来越大，即：`(n-1)/n` ,`n`为该节内容包含的句子数量。当chunk越长，相同的前缀内容就会越多，进而无法有效辨别加入完全不同语境句子带来的变化。

本项目参考langchain中的semantic segment方式，用`[sentence[i-1],sentence[i],sentence[i+1]]`和`[sentence[i-2],sentence[i-1],sentence[i]]` 之间的相似度，记录第`i`句是否和`i-1`句具备相同语境(P([u<sub>0~i</sub>]|[u<sub>0~i-1</sub>]))，可以得到共计`n-1`个相似度。
langchain默认采用大于所有相似度95%(可自行调整)的值作为切分阈值`threshold`，因此可以将文本切分为`19/20*n(向下取整)`个chunk。
#### 衰减策略
但是如果极端讲，仍然存在某一个`chunk`过长的可能性。因此在本项目中，特意设计一个衰减因子，随着`chunk`内句子的增加，减少后续句子的相似度，达到避免这一情况的目的。
该衰减因子概念可以等价为设计一套函数，值域为`(0,1)`，定义域为`(0,+∞)`，满足单调递增。 项目中该函数设定为`f(j) = e^(-1/j)`，其中`j`为当前chunk的长度。

因此，当前长度为`j`的chunk的切分阈值由`max(threshold, f(j))`决定。

## 写在最后
基于知识库的大模型回答效果如何，不仅仅取决于切分策略，和检索策略，添加元数据与否，提问优化（涉及问题重写，上下文问答理解等等）方方面面息息相关。

本项目仅仅聚焦于切分小点。

## 参考文献
1. Gao Y, Xiong Y, Gao X, et al. Retrieval-augmented generation for large language models: A survey[J]. arXiv preprint arXiv:2312.10997, 2023.
2. Zhao P, Zhang H, Yu Q, et al. Retrieval-augmented generation for ai-generated content: A survey[J]. arXiv preprint arXiv:2402.19473, 2024.
3. N. F. Liu, K. Lin, J. Hewitt et al., “Lost in the middle: How language models use long contexts,” arxiv:2307.03172, 2023
