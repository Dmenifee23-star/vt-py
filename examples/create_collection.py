# Copyright © 2021 The vt-py authors. All Rights Reserved.
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

"""How to create a collection in VirusTotal."""

import argparse
import json
import io
import vt


def create_collection(client, name, file):
  """Creates a reference in VirusTotal.

  Args:
    client: VirusTotal client.
    name: Collection's name.
    file: File containing the IOCs to add to the collection.

  Returns:
    The new collection object.
  """

  collection_obj = vt.Object('collection', obj_attributes={'name': name})
  collection_obj.set_data('raw_items', file.read())
  return client.post_object('/collections', obj=collection_obj)


def generate_ui_link(collection_id):
  return "https://www.virustotal.com/gui/collection/%s" % collection_id


def main():
  parser = argparse.ArgumentParser(
      description='Create a VirusTotal collection.')

  parser.add_argument('--apikey', required=True, help='your VirusTotal API key')
  parser.add_argument('--name', required=True, help='collection\'s name')

  args = parser.parse_args()
  client = vt.Client(args.apikey)

  # Typical usage would be to create a collection from a text file with IOCs:
  # with open('iocs.txt') as f:
  #   collection_obj = create_collection(client, args.name, f)

  # Or using a string with the IOCs.
  iocs = io.StringIO('www.example.com\nhttps://www.hooli.com')
  collection_obj = create_collection(client, args.name, iocs)

  client.close()
  print(json.dumps(collection_obj.to_dict(), indent=2))

  print("Link:\n%s" % generate_ui_link(collection_obj.id))


if __name__ == '__main__':
  main()
