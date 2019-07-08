from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import h5py
import json
import os
import sys
from tqdm import tqdm


def build_elmo():
    token_ph = tf.placeholder(tf.string, [None, None])
    len_ph = tf.placeholder(tf.int32, [None])
    elmo_module = hub.Module("https://tfhub.dev/google/elmo/2")
    lm_embeddings = elmo_module(
        inputs={"tokens": token_ph, "sequence_len": len_ph},
        signature="tokens", as_dict=True)
    word_emb = lm_embeddings["word_emb"]
    lm_emb = tf.stack([tf.concat([word_emb, word_emb], -1),
                       lm_embeddings["lstm_outputs1"],
                       lm_embeddings["lstm_outputs2"]], -1)
    return token_ph, len_ph, lm_emb


def cache_dataset(data_path, session, token_ph, len_ph, lm_emb, out_file):
    with open(data_path) as in_file:
        for doc_num, line in enumerate(in_file.readlines()):
            example = json.loads(line)
            sentences = example["sentences"]
            max_sentence_length = max(len(s) for s in sentences)
            tokens = [[""] * max_sentence_length for _ in sentences]
            text_len = np.array([len(s) for s in sentences])
            for i, sentence in enumerate(sentences):
                for j, word in enumerate(sentence):
                    tokens[i][j] = word
            tokens = np.array(tokens)
            tf_lm_emb = session.run(lm_emb, feed_dict={
                token_ph: tokens,
                len_ph: text_len
            })
            file_key = example["doc_key"].replace("/", ":")
            group = out_file.create_group(file_key)
            for i, (e, l) in enumerate(zip(tf_lm_emb, text_len)):
                e = e[:l, :, :]
                group[str(i)] = e
            if doc_num % 10 == 0:
                print("Cached {} documents in {}".format(doc_num + 1, data_path))


def cache_large_dataset(data_path, session, token_ph, len_ph, lm_emb, out_file):
    with open(data_path) as in_file:
        for doc_num, line in enumerate(in_file.readlines()):
            example = json.loads(line)
            sentences = example["sentences"]
            all_embedding = list()
            all_text_len = np.array([len(s) for s in sentences])
            max_sentence_length = max(len(s) for s in sentences)
            for s in sentences:
                tmps = [s]
                tokens = [[""] * max_sentence_length for _ in tmps]
                text_len = np.array([len(s) for s in tmps])
                for i, sentence in enumerate(tmps):
                    for j, word in enumerate(sentence):
                        tokens[i][j] = word
                tokens = np.array(tokens)
                tf_lm_emb = session.run(lm_emb, feed_dict={
                    token_ph: tokens,
                    len_ph: text_len
                })
                all_embedding.append(tf_lm_emb[0])
            file_key = example["doc_key"].replace("/", ":")
            group = out_file.create_group(file_key)
            for i, (e, l) in enumerate(zip(all_embedding, all_text_len)):
                e = e[:l, :, :]
                group[str(i)] = e
            if doc_num % 10 == 0:
                print("Cached {} documents in {}".format(doc_num + 1, data_path))
file_names = ['conll_data/train.jsonlines',
              'conll_data/dev.jsonlines', 'conll_data/test.jsonlines', 'medical_data/train.jsonlines', 'medical_data/test.jsonlines']
os.environ["CUDA_VISIBLE_DEVICES"] = "3"
if __name__ == "__main__":
    token_ph, len_ph, lm_emb = build_elmo()
    with tf.Session() as session:
        session.run(tf.global_variables_initializer())
        with h5py.File("elmo_cache.hdf5", "w") as out_file:
            for json_filename in file_names:
                print('we are working on file:', json_filename)
                if 'medical' in json_filename:
                    cache_large_dataset(json_filename, session, token_ph, len_ph, lm_emb, out_file)
                else:
                    cache_large_dataset(json_filename, session, token_ph, len_ph, lm_emb, out_file)