#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
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
#

import hashlib
import urllib
import urllib2
import sys
import time
import getpass
import appengine_rpc

LIST_DELIMITER = '\n'
TUPLE_DELIMITER = '|'
MAX_BATCH_SIZE = 1000000
MAX_BATCH_COUNT = 100
MAX_BATCH_FILE_SIZE = 200000
BATCH_OVERHEAD = 500
BASE_DIR = "fetchserver"

verbosity = 1

def GetUserCredentials():
	"""Prompts the user for a username and password."""
	email = None
	if email is None:
		email = raw_input('Email: ')
	password_prompt = 'Password for %s: ' % email
	password = getpass.getpass(password_prompt)
	return (email, password)

class UploadBatcher(object):
	"""Helper to batch file uploads."""

	def __init__(self, what, app_id, version, server):
		"""Constructor.

		Args:
			what: Either 'file' or 'blob' or 'errorblob' indicating what kind of
				objects this batcher uploads.	Used in messages and URLs.
			app_id: The application ID.
			version: The application version string.
			server: The RPC server.
		"""
		assert what in ('file', 'blob', 'errorblob'), repr(what)
		self.what = what
		self.app_id = app_id
		self.version = version
		self.server = server
		self.single_url = '/api/appversion/add' + what
		self.batch_url = self.single_url + 's'
		self.batching = True
		self.batch = []
		self.batch_size = 0

	def SendBatch(self):
		"""Send the current batch on its way.

		If successful, resets self.batch and self.batch_size.

		Raises:
			HTTPError with code=404 if the server doesn't support batching.
		"""
		boundary = 'boundary'
		parts = []
		for path, payload, mime_type in self.batch:
			while boundary in payload:
				boundary += '%04x' % random.randint(0, 0xffff)
				assert len(boundary) < 80, 'Unexpected error, please try again.'
			part = '\n'.join(['', 'X-Appcfg-File: %s' % urllib.quote(path), 'X-Appcfg-Hash: %s' % _Hash(payload), 'Content-Type: %s' % mime_type, 'Content-Length: %d' % len(payload), 'Content-Transfer-Encoding: 8bit', '', payload, ])
			parts.append(part)
		parts.insert(0, 'MIME-Version: 1.0\n' 'Content-Type: multipart/mixed; boundary="%s"\n' '\n' 'This is a message with multiple parts in MIME format.' % boundary)
		parts.append('--\n')
		delimiter = '\n--%s' % boundary
		payload = delimiter.join(parts)
		self.server.Send(self.batch_url, payload=payload, content_type='message/rfc822', app_id=self.app_id, version=self.version)
		self.batch = []
		self.batch_size = 0

	def SendSingleFile(self, path, payload, mime_type):
		"""Send a single file on its way."""
		self.server.Send(self.single_url, payload=payload, content_type=mime_type, path=path, app_id=self.app_id, version=self.version)

	def Flush(self):
		"""Flush the current batch.

		This first attempts to send the batch as a single request; if that
		fails because the server doesn't support batching, the files are
		sent one by one, and self.batching is reset to False.

		At the end, self.batch and self.batch_size are reset.
		"""
		if not self.batch:
			return
		try:
			self.SendBatch()
		except urllib2.HTTPError, err:
			if err.code != 404:
				raise
			self.batching = False
			for path, payload, mime_type in self.batch:
				self.SendSingleFile(path, payload, mime_type)
			self.batch = []
			self.batch_size = 0

	def AddToBatch(self, path, payload, mime_type):
		"""Batch a file, possibly flushing first, or perhaps upload it directly.

		Args:
			path: The name of the file.
			payload: The contents of the file.
			mime_type: The MIME Content-type of the file, or None.

		If mime_type is None, application/octet-stream is substituted.
		"""
		if not mime_type:
			mime_type = 'application/octet-stream'
		size = len(payload)
		if size <= MAX_BATCH_FILE_SIZE:
			if (len(self.batch) >= MAX_BATCH_COUNT or self.batch_size + size > MAX_BATCH_SIZE):
				self.Flush()
			if self.batching:
				self.batch.append((path, payload, mime_type))
				self.batch_size += size + BATCH_OVERHEAD
				return
		self.SendSingleFile(path, payload, mime_type)

def StatusUpdate(msg):
	"""Print a status message to stderr.

	If 'verbosity' is greater than 0, print the message.

	Args:
		msg: The string to print.
	"""
	if verbosity > 0:
		print >>sys.stderr, msg

def _Hash(content):
	"""Compute the hash of the content.

	Args:
		content: The data to hash as a string.

	Returns:
		The string representation of the hash.
	"""
	m = hashlib.sha1()
	m.update(content)
	h = m.hexdigest()
	return '%s_%s_%s_%s_%s' % (h[0:8], h[8:16], h[16:24], h[24:32], h[32:40])

def BuildClonePostBody(file_tuples):
	"""Build the post body for the /api/clone{files,blobs,errorblobs} urls.
	
	Args:
	  file_tuples: A list of tuples.  Each tuple should contain the entries
	    appropriate for the endpoint in question.
	
	Returns:
	  A string containing the properly delimited tuples.
	"""
	file_list = []
	for tup in file_tuples:
		path = tup[0]
		tup = tup[1:]
		file_list.append(TUPLE_DELIMITER.join([path] + list(tup)))
	return LIST_DELIMITER.join(file_list)

def RetryWithBackoff(initial_delay, backoff_factor, max_delay, max_tries, callable_func):
	"""Calls a function multiple times, backing off more and more each time.

	Args:
		initial_delay: Initial delay after first try, in seconds.
		backoff_factor: Delay will be multiplied by this factor after each try.
		max_delay: Max delay factor.
		max_tries: Maximum number of tries.
		callable_func: The method to call, will pass no arguments.

	Returns:
		True if the function succeded in one of its tries.

	Raises:
		Whatever the function raises--an exception will immediately stop retries.
	"""
	delay = initial_delay
	if callable_func():
		return True
	while max_tries > 1:
		StatusUpdate('Will check again in %s seconds.' % delay)
		time.sleep(delay)
		delay *= backoff_factor
		if max_delay and delay > max_delay:
			delay = max_delay
		max_tries -= 1
		if callable_func():
			return True
	return False

class AppVersionUpload(object):
	"""Provides facilities to upload a new appversion to the hosting service.

	Attributes:
		server: The AbstractRpcServer to use for the upload.
		config: The AppInfoExternal object derived from the app.yaml file.
		app_id: The application string from 'config'.
		version: The version string from 'config'.
		files: A dictionary of files to upload to the server, mapping path to
			hash of the file contents.
		in_transaction: True iff a transaction with the server has started.
			An AppVersionUpload can do only one transaction at a time.
		deployed: True iff the Deploy method has been called.
	"""

	def __init__(self, server, app_id):
		"""Creates a new AppVersionUpload.

		Args:
			server: The RPC server to use. Should be an instance of HttpRpcServer or
				TestRpcServer.
		"""
		self.server = server
		self.app_id = app_id
		self.version = 1
		self.yaml = """
application: %s
version: 1
runtime: python
api_version: 1

handlers:

- url: /fetch.py
  script: fetch.py
""" % app_id
		self.files = {}
		self.in_transaction = False
		self.deployed = False
		self.batching = True
		self.file_batcher = UploadBatcher('file', self.app_id, self.version, self.server)

	def AddFile(self, path, file_handle):
		"""Adds the provided file to the list to be pushed to the server.

		Args:
			path: The path the file should be uploaded as.
			file_handle: A stream containing data to upload.
		"""
		assert not self.in_transaction, 'Already in a transaction.'
		assert file_handle is not None
		pos = file_handle.tell()
		content_hash = _Hash(file_handle.read())
		file_handle.seek(pos, 0)
		self.files[path] = content_hash

	def Begin(self):
		"""Begins the transaction, returning a list of files that need uploading.

		All calls to AddFile must be made before calling Begin().

		Returns:
			A list of pathnames for files that should be uploaded using UploadFile()
			before Commit() can be called.
		"""
		assert not self.in_transaction, 'Already in a transaction.'
		StatusUpdate('Initiating update.')
		self.server.Send('/api/appversion/create', app_id=self.app_id, version=self.version, payload=self.yaml)
		self.in_transaction = True
		files_to_clone = []
		for path, content_hash in self.files.iteritems():
			files_to_clone.append((path, content_hash))
		files_to_upload = {}

		def CloneFiles(url, files, file_type):
			"""Sends files to the given url.

			Args:
				url: the server URL to use.
				files: a list of files
				file_type: the type of the files
			"""
			if not files:
				return
			result = self.server.Send(url, app_id=self.app_id, version=self.version, payload=BuildClonePostBody(files))
			if result:
				files_to_upload.update(dict((f, self.files[f]) for f in result.split(LIST_DELIMITER)))

		CloneFiles('/api/appversion/clonefiles', files_to_clone, 'application')
		self.files = files_to_upload
		return sorted(files_to_upload.iterkeys())

	def UploadFile(self, path, file_handle):
		"""Uploads a file to the hosting service.

		Must only be called after Begin().
		The path provided must be one of those that were returned by Begin().

		Args:
			path: The path the file is being uploaded as.
			file_handle: A file-like object containing the data to upload.

		Raises:
			KeyError: The provided file is not amongst those to be uploaded.
		"""
		assert self.in_transaction, 'Begin() must be called before UploadFile().'
		if path not in self.files:
			raise KeyError('File \'%s\' is not in the list of files to be uploaded.' % path)
		del self.files[path]
		self.file_batcher.AddToBatch(path, file_handle.read(), None)

	def Commit(self):
		"""Commits the transaction, making the new app version available.

		All the files returned by Begin() must have been uploaded with UploadFile()
		before Commit() can be called.

		This tries the new 'deploy' method; if that fails it uses the old 'commit'.

		Raises:
			Exception: Some required files were not uploaded.
		"""
		assert self.in_transaction, 'Begin() must be called before Commit().'
		if self.files:
			raise Exception('Not all required files have been uploaded.')
		try:
			self.Deploy()
			if not RetryWithBackoff(1, 2, 60, 20, self.IsReady):
				raise Exception('Version not ready.')
			self.StartServing()
		except urllib2.HTTPError, e:
			if e.code != 404:
				raise
			StatusUpdate('Closing update.')
			self.server.Send('/api/appversion/commit', app_id=self.app_id, version=self.version)
			self.in_transaction = False

	def Deploy(self):
		"""Deploys the new app version but does not make it default.

		All the files returned by Begin() must have been uploaded with UploadFile()
		before Deploy() can be called.

		Raises:
			Exception: Some required files were not uploaded.
		"""
		assert self.in_transaction, 'Begin() must be called before Deploy().'
		if self.files:
			raise Exception('Not all required files have been uploaded.')
		StatusUpdate('Deploying new version.')
		self.server.Send('/api/appversion/deploy', app_id=self.app_id, version=self.version)
		self.deployed = True

	def IsReady(self):
		"""Check if the new app version is ready to serve traffic.

		Raises:
			Exception: Deploy has not yet been called.

		Returns:
			True if the server returned the app is ready to serve.
		"""
		assert self.deployed, 'Deploy() must be called before IsReady().'
		StatusUpdate('Checking if new version is ready to serve.')
		result = self.server.Send('/api/appversion/isready', app_id=self.app_id, version=self.version)
		return result == '1'

	def StartServing(self):
		"""Start serving with the newly created version.

		Raises:
			Exception: Deploy has not yet been called.
		"""
		assert self.deployed, 'Deploy() must be called before IsReady().'
		StatusUpdate('Closing update: new version is ready to start serving.')
		self.server.Send('/api/appversion/startserving', app_id=self.app_id, version=self.version)
		self.in_transaction = False

	def Rollback(self):
		"""Rolls back the transaction if one is in progress."""
		if not self.in_transaction:
			return
		StatusUpdate('Rolling back the update.')
		self.server.Send('/api/appversion/rollback', app_id=self.app_id, version=self.version)
		self.in_transaction = False
		self.files = {}

	def DoUpload(self):
		"""Uploads a new appversion with the given config and files to the server."""
		self.AddFile("fetch.py", open("%s/fetch.py" % BASE_DIR, "r"))
		try:
			missing_files = self.Begin()
			if missing_files:
				StatusUpdate('Uploading %d files and blobs.' % len(missing_files))
				num_files = 0
				for missing_file in missing_files:
					file_handle = open("%s/%s" % (BASE_DIR, missing_file), "r")
					try:
						self.UploadFile(missing_file, file_handle)
					finally:
						file_handle.close()
					num_files += 1
				self.file_batcher.Flush()
				StatusUpdate('Uploaded %d files and blobs' % num_files)
			self.Commit()
		except:
			self.Rollback()
			raise

def main():
	if len(sys.argv) == 2 and sys.argv[1] != "update" and sys.argv[1] != "rollback":
		print "Usage: %s [update|rollback]" % sys.argv[0]
		return
	rpc_server = appengine_rpc.HttpRpcServer("appengine.google.com", GetUserCredentials, "GAppProxy Uploader", "0.0.1", host_override=None, save_cookies=True, auth_tries=3, account_type='HOSTED_OR_GOOGLE', secure=True)
	appversion = AppVersionUpload(rpc_server, raw_input("AppID: "))
	if len(sys.argv) == 2 and sys.argv[1] == "rollback":
		appversion.in_transaction = True
		appversion.Rollback()
	else:	# update
		appversion.DoUpload()
		time.sleep(30)

if __name__ == "__main__":
	main()
