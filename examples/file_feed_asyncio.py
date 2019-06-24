#!/usr/local/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2019 The vt-py authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This example program shows how to use the vt-py asynchronous API for getting
the VirusTotal file feed in an efficient manner. For using this program you
need an API key with privileges for using the feed API.
"""

import argparse
import asyncio
import aiohttp
import functools
import json
import os
import signal
import vt


class FeedReader:

  def __init__(self, apikey, output_dir, num_workers=4, cursor=None):
    self._apikey = apikey
    self._aborted = False
    self._cursor = cursor
    self._output_dir = output_dir
    self._num_workers = num_workers
    self._queue = asyncio.Queue(maxsize=num_workers)

  async def _get_from_feed_and_enqueue(self):
    """Get files from the file feed and put them into a queue."""
    async with vt.Client(self._apikey) as client:
      feed = client.feed(vt.FeedType.FILES, cursor=self._cursor)
      async for file_obj in feed:
        await self._queue.put(file_obj)
        if self._aborted:
          break
      self._cursor = feed.cursor

  async def _process_files_from_queue(self):
    """Process files put in the queue by _get_from_feed_and_enqueue.

    This function runs in a loop until the feed reader is aborted, once aborted
    it keeps processing any file that remains in the queue.
    """
    async with vt.Client(self._apikey) as client:
      while not self._aborted or not self._queue.empty():
        file_obj = await self._queue.get()
        # The URL for downloading the file comes as a context attribute named
        # 'download_url'.
        download_url = file_obj.context_attributes['download_url']
        file_path = os.path.join(self._output_dir, file_obj.id)
        response = await client.get_async(download_url)
        data = await response.read()
        # Write a file <sha256>.json with file's metadata and another file
        # named <sha256> with the file's content.
        with open(file_path + '.json', mode='w') as f:
          f.write(json.dumps(file_obj.to_dict()))
        with open(file_path, mode='wb') as f:
          f.write(data)
        self._queue.task_done()
        print(file_obj.id)

  def abort(self):
    self._aborted = True

  def cursor(self):
    return self._cursor

  def run(self):

    loop = asyncio.get_event_loop()
    # Create a task that read file object's from the feed and put them in a
    # queue.
    loop.create_task(self._get_from_feed_and_enqueue())

    # Create multiple tasks that read file object's from the queue, download
    # the file's content, and create the output files.
    self._worker_tasks = []
    for i in range(self._num_workers):
      self._worker_tasks.append(
          loop.create_task(self._process_files_from_queue()))

    # If the program is interrupted, abort it gracefully.
    signals = (signal.SIGINT,)
    for s in signals:
      loop.add_signal_handler(s, self.abort)

    # Wait until all worker tasks has completed.
    loop.run_until_complete(asyncio.gather(*self._worker_tasks))
    loop.close()


def main():

  parser = argparse.ArgumentParser(
      description='Get files from the VirusTotal feed.')

  parser.add_argument('--apikey',
      required=True, help='Your VirusTotal API key')

  parser.add_argument('--cursor',
      required=False, help='Cursor indicating where to start', default=None)

  parser.add_argument('--output',
      default='./file-feed', help='Path to output dir')

  parser.add_argument('--num_workers', type=int,
      required=False, help='Number of workers', default=4)

  args = parser.parse_args()

  if not os.path.exists(args.output):
    os.makedirs(args.output)

  feed_reader = FeedReader(
      args.apikey,
      args.output,
      num_workers=args.num_workers,
      cursor=args.cursor)

  feed_reader.run()

  print("\ncontinuation cursor: {}".format(feed_reader.cursor()))


if __name__ == '__main__':
  main()
