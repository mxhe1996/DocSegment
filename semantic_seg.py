import math
import sys
import time
import re
import numpy as np

from text2vec import SimpleEmbeddingModel


class SemanticTextSplitter:

    def __init__(self, embed_model: SimpleEmbeddingModel, semantic_field=1, risk_param=1.11):
        self.semantic_field = semantic_field
        self.embed_model = embed_model
        self.risk_param = risk_param
        self.embed_model.load_model('spark')
        self.meaningless_filter_re = r'<.+>|\n'

    def character_filter(self, ori_content: str) -> str:
        processed_content = re.sub(self.meaningless_filter_re, '', ori_content)
        print(processed_content)
        return processed_content

    def compute_similarity_cos(self, after_vector, before_vector):
        after_np = np.array(after_vector)
        before_np = np.array(before_vector)
        sim = np.divide(before_np.dot(after_np),
                        np.multiply(np.sqrt(after_np.dot(after_np)), np.sqrt(before_np.dot(before_np))))
        print("向量相似度:" + str(sim))
        return sim

    # 模拟衰减因子
    def dynamic_segment_factory(self, chunk_size):
        return math.pow(math.e, -1 / math.pow((chunk_size - 1 + 1e-10), self.risk_param))

    def semantic_split_text(self, text: str):
        # 字符清洗
        character_clean_content = self.character_filter(text)
        # 中文文本分割
        single_sentences = re.split(r'(?<=[。？！])', character_clean_content)

        # semantic_field = 1
        combined_context_sentence = []
        for i in range(len(single_sentences)):
            print('\r', end='')
            print('进度：{}%'.format(i * 100 // len(single_sentences)), "▓" * (i // 2), end='')
            time.sleep(0.6)
            sys.stdout.flush()
            combine = "".join(
                single_sentences[
                    max(0, i - self.semantic_field):min(i + self.semantic_field + 1, len(single_sentences))])
            vec = self.embed_model.embed_query(combine)
            combined_context_sentence.append({'index': i, 'content': combine, 'vector': vec})

        # 计算距离
        similarity_array = []
        for _ in range(len(combined_context_sentence) - 1):
            similarity = self.compute_similarity_cos(combined_context_sentence[_]['vector'],
                                                     combined_context_sentence[_ + 1]['vector'])
            similarity_array.append(similarity)

        segment_threshold = np.percentile(similarity_array, 95)

        chunk_segment = []
        chunk_start_, segment_index = 0, 1
        while segment_index < len(similarity_array):
            if similarity_array[segment_index] < max(segment_threshold,
                                                     self.dynamic_segment_factory(segment_index - chunk_start_)):
                segment_index += 1
            else:
                chunk_segment.append({'chunk_content': single_sentences[chunk_start_:segment_index - 1]})
                chunk_start_ = segment_index
                segment_index += 1

        chunk_segment.append(single_sentences[chunk_start_:])
        return chunk_segment




