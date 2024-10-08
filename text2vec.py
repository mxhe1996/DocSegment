from langchain_community.embeddings import SparkLLMTextEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_random_exponential
import requests
import yaml
import os


class SimpleEmbeddingModel:

    _cache = {}

    _config_yaml = ['config-local.yaml', 'config.yaml']

    def __init__(self, ):
        self.config_path = None
        self.model_config = self.__load_config()
        self.model_dict = self.load_model_defines()
        self.current_model = None
        self.current_model_name = None

    def __load_config(self) -> dict:
        candidate_configs = os.listdir(os.getcwd())
        for config_yaml in self._config_yaml:
            if config_yaml in candidate_configs:
                self.config_path = os.path.join(os.getcwd(), config_yaml)
                break

        if self.config_path is None:
            raise Exception('找不到对应的config-local.yaml或者config.yaml')

        with open(self.config_path, 'r') as file:
            config = list(yaml.safe_load_all(file))[0]['embedding_model']
        return config

    def load_model_defines(self):
        return {
            'spark': self.__spark_model,
            'openai': self.__openai_model,
            'bge-m3': self.__bge_m3_model_from_qwen
        }

    def __spark_model(self):
        spark_app_id = self.model_config['spark']['spark_app_id']
        spark_api_key = self.model_config['spark']['spark_api_key']
        spark_api_secret = self.model_config['spark']['spark_api_secret']
        if spark_api_secret is None or spark_app_id is None or spark_api_key is None:
            print("===================== failed loading spark model =====================")
            raise Exception('配置文件未明确指明spark模型相关参数')
        print("===================== success loading spark model =====================")
        return SparkLLMTextEmbeddings(spark_app_id=spark_app_id,
                                      spark_api_secret=spark_api_secret,
                                      spark_api_key=spark_api_key)

    def __openai_model(self):
        openai_api_key = self.model_config['openai']['api_key']
        if openai_api_key is None:
            print("===================== failed loading openai model =====================")
            raise Exception('配置文件未明确指明openai模型相关参数')
        os.environ['OPENAI_API_KEY'] = openai_api_key
        print("===================== success loading openai model =====================")
        return OpenAIEmbeddings()

    def __bge_m3_model_from_qwen(self):
        model = self.model_config['bge_m3']['model_name']
        url = self.model_config['bge_m3']['url']
        if model is None or url is None:
            print("===================== failed loading bgem3 qwen model =====================")
            raise Exception('配置文件未明确指明本地模型bge-m3相关参数')
        print("===================== success loading bgem3 qwen model =====================")
        return LocalEmbeddingModel(model, url)

    def load_model(self, model_type: str):
        if self.current_model is not None and model_type == self.current_model_name:
            return self.current_model
        type_lower = model_type.lower()
        assert type_lower in self.model_dict.keys()
        # cache model
        if type_lower in self._cache.keys():
            print('load {} from cache'.format(type_lower))
            return self._cache.get(type_lower)

        model_define = self.model_dict.get(type_lower)
        self.current_model = model_define()
        self.current_model_name = type_lower
        self._cache[type_lower] = self.current_model
        # return self.current_model

    def embed_query(self, text: str, model_name=None):
        if model_name is None:
            if self.current_model is None:
                return None
            return self.current_model.embed_query(text)
        self.load_model(model_name)

        return self.current_model.embed_query(text)

    @property
    def cache(self):
        return self._cache


class LocalEmbeddingModel:
    def __init__(self, model, url):
        self.model = model
        self.url = url

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def embed_query(self, text):
        post_json = {"text": text}
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.url, json=post_json, headers=headers)
        data_json = response.json()
        return data_json["embeddings"]


# emb_model = SimpleEmbeddingModel()
# emb_model.load_model('bge-m3')
# emb_model.load_model('spark')
# # emb_model.load_model('bge-m3')
# vec = emb_model.embed_query("上海自来水来自海上", 'bge-m3')
# print(vec)
# # bge_model = bge_model_define()
# # bge_model.embed_query()
#
# print(1)

