# MIT License
#
# Copyright (c) 2019 Tom Runia
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to conditions.
#
# Author: Deep Learning Course | Fall 2019
# Date Created: 2019-09-06
################################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import csv
import time
from datetime import datetime
import argparse

import numpy as np
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from torch.utils.tensorboard import SummaryWriter

from part2.dataset import TextDataset
from part2.model import TextGenerationModel


# Plot summary writer downloads
def plot_training_results():
    with open('runs/Nov27_00-27-27_r30n1.lisa.surfsara.nl/accuracy.csv', 'r') as f:
        reader = csv.reader(f)
        training_accuracy = list(reader)

    with open('runs/Nov27_00-27-27_r30n1.lisa.surfsara.nl/loss.csv', 'r') as f:
        reader = csv.reader(f)
        training_losses = list(reader)

    losses = [float(i[2]) for i in training_losses[1:]]
    loss_steps = [int(i[1]) for i in training_losses[1:]]

    accuracies = [float(i[2]) for i in training_accuracy[1:]]
    acc_steps = [int(i[1]) for i in training_accuracy[1:]]

    fig = plt.figure(figsize=(20, 10), dpi=150)
    fig.suptitle('Accuracy and Loss during training', fontsize=36)

    for i, (value, steps, title) in enumerate([(accuracies, acc_steps, "Accuracy"), (losses, loss_steps, "Loss")]):
        ax = fig.add_subplot(1, 2, i + 1)
        ax.plot(steps, value, linewidth=2, color="tomato", label="Loss")

        ax.tick_params(labelsize=16)

        ax.set_xlabel('Steps', fontsize=24)
        ax.set_ylabel('{}'.format(title), fontsize=24)

    if not os.path.exists('part2/figures/'):
        os.makedirs('part2/figures/')

    plt.savefig("part2/figures/acc_and_loss.png")
    plt.show()


def sample_from_model(config, step, model, dataset):
    device = config.device
    title_string = "[{}] Train Step {:04d}/{:04d}, Sample Length: {} \n"
    seq_string = "Temperature: {}, Text: {} \n"

    for t in [15, 30, 50, 100]:
        seq_greedy = generate_from_model(model, dataset, t, sampling_type="greedy", tau=1.0, device=device)
        seq_t05 = generate_from_model(model, dataset, t, sampling_type="use_temperature", tau=0.5, device=device)
        seq_t10 = generate_from_model(model, dataset, t, sampling_type="use_temperature", tau=1.0, device=device)
        seq_t20 = generate_from_model(model, dataset, t, sampling_type="use_temperature", tau=2.0, device=device)

        greedy_string = seq_string.format("Greedy", seq_greedy)
        seq_t05_string = seq_string.format("0.5", seq_t05)
        seq_t10_string = seq_string.format("1.0", seq_t10)
        seq_t20_string = seq_string.format("2.0", seq_t20)

        with open("samples_over_training.txt", "a") as text_file:
            text_file.write(
                title_string.format(datetime.now().strftime("%Y-%m-%d %H:%M"), step, int(config.train_steps), t))
            text_file.write(greedy_string)
            text_file.write(seq_t05_string)
            text_file.write(seq_t10_string)
            text_file.write(seq_t20_string)
            text_file.write("\n \n")


def generate_from_model(model, dataset, T=30, sampling_type="greedy", tau=1.0, device="cpu"):
    vocab_size = dataset.vocab_size
    hidden = None

    sample_char = torch.randint(vocab_size, size=(1, 1), device=device)
    final_sequence = [sample_char.item()]

    for t in range(T - 1):

        with torch.no_grad():
            model_output, hidden = model.forward(sample_char, hidden)

        if sampling_type == "greedy":
            sm = torch.softmax(model_output, dim=1)
            sample_char = torch.argmax(sm, dim=1)

        elif sampling_type == "use_temperature":
            sm = torch.softmax(tau * model_output, dim=1).view(-1)
            sample_char = torch.multinomial(sm, 1)[:, None]

        else:
            print("Unknown sampling type")
            break

        final_sequence.append(sample_char.item())

    return dataset.convert_to_string(final_sequence)


################################################################################

def train(config):
    seed = 42
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Initialize the device which to run the model on
    device = torch.device(config.device)

    writer = SummaryWriter()

    seq_length = config.seq_length
    batch_size = config.batch_size
    lstm_num_hidden = config.lstm_num_hidden
    lstm_num_layers = config.lstm_num_layers
    dropout_keep_prob = config.dropout_keep_prob

    # Initialize the dataset and data loader (note the +1)
    dataset = TextDataset(config.txt_file, seq_length)
    data_loader = DataLoader(dataset, batch_size, num_workers=1)

    vocab_size = dataset.vocab_size

    # Initialize the model that we are going to use
    model = TextGenerationModel(batch_size, seq_length, vocab_size, lstm_num_hidden, lstm_num_layers, dropout_keep_prob,
                                device)
    model.to(device)

    # Setup the loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)
    lr_scheduler = optim.lr_scheduler.StepLR(optimizer, config.learning_rate_step, config.learning_rate_decay)

    for step, (batch_inputs, batch_targets) in enumerate(data_loader):

        # Only for time measurement of step through network
        t1 = time.time()

        #######################################################
        # Add more code here ...
        #######################################################

        # To onehot represetation of input or embedding => decided for embedding
        # batch_inputs = F.one_hot(batch_inputs, vocab_size).type(torch.FloatTensor).to(device)
        batch_inputs = batch_inputs.to(device)
        batch_targets = batch_targets.to(device)

        train_output, _ = model.forward(batch_inputs)

        loss = criterion(train_output, batch_targets)
        accuracy = torch.sum(torch.eq(torch.argmax(train_output, dim=1), batch_targets)).item() / (
                batch_targets.size(0) * batch_targets.size(1))

        writer.add_scalar('Loss/train', loss.item(), step)
        writer.add_scalar('Accuracy/train', accuracy, step)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        lr_scheduler.step(step)

        # Just for time measurement
        t2 = time.time()
        examples_per_second = config.batch_size / float(t2 - t1)

        if step % config.print_every == 0:
            print("[{}] Train Step {:04d}/{:04d}, Batch Size = {}, Examples/Sec = {:.2f}, "
                  "Accuracy = {:.2f}, Loss = {:.3f}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M"), step,
                int(config.train_steps), config.batch_size, examples_per_second,
                accuracy, loss
            ))

        if step % config.sample_every == 0:
            # Generate some sentences by sampling from the model
            sample_from_model(config, step, model, dataset)

        if step == config.train_steps:
            # If you receive a PyTorch data-loader error, check this bug report:
            # https://github.com/pytorch/pytorch/pull/9655
            break

    print('Done training.')
    torch.save(model, "trained_model_part2.pth")
    writer.close()


################################################################################
################################################################################

if __name__ == "__main__":
    # Parse training configuration
    parser = argparse.ArgumentParser()

    # Model params
    parser.add_argument('--txt_file', type=str, required=True, help="Path to a .txt file to train on")
    parser.add_argument('--seq_length', type=int, default=30, help='Length of an input sequence')
    parser.add_argument('--lstm_num_hidden', type=int, default=128, help='Number of hidden units in the LSTM')
    parser.add_argument('--lstm_num_layers', type=int, default=2, help='Number of LSTM layers in the model')

    # Training params
    parser.add_argument('--batch_size', type=int, default=64, help='Number of examples to process in a batch')
    parser.add_argument('--learning_rate', type=float, default=2e-3, help='Learning rate')

    # It is not necessary to implement the following three params, but it may help training.
    parser.add_argument('--learning_rate_decay', type=float, default=0.96, help='Learning rate decay fraction')
    parser.add_argument('--learning_rate_step', type=int, default=5000, help='Learning rate step')
    parser.add_argument('--dropout_keep_prob', type=float, default=1.0, help='Dropout keep probability')

    parser.add_argument('--train_steps', type=int, default=1e6, help='Number of training steps')
    parser.add_argument('--max_norm', type=float, default=5.0, help='--')

    # Misc params
    parser.add_argument('--summary_path', type=str, default="./summaries/", help='Output path for summaries')
    parser.add_argument('--print_every', type=int, default=5, help='How often to print training progress')
    parser.add_argument('--sample_every', type=int, default=100, help='How often to sample from the model')

    config = parser.parse_args()

    # Train the model
    train(config)
