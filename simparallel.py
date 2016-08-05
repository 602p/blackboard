import zipfile, paramiko, glob, importlib, os, datetime, sys, collections

def waitfor(t):
	stdin, stdout, stderr=t
	stdout.channel.recv_exit_status()
	return t

class Task:
	def __init__(self, taskname, servers, files, command, use_workers, delete, returns, returnto):
		self.taskname=taskname
		self.servers=servers
		self.server_order={}
		for n,k in enumerate(servers.keys()):
			self.server_order[k]=n
		self.files_proto=files
		self.command=command
		self.use_workers=use_workers
		self.delete=delete
		self.returns=returns
		self.returnto=returnto
		self.nproc=None

	def log(self, text):
		ftext=str(datetime.datetime.now())+":\t"+text
		print(ftext)
	
	def build_zip(self):
		self.files=[]
		for item in self.files_proto:
			for fn in glob.glob(item):
				if not os.path.isdir(fn) and fn!="application.zip":
					self.files.append(fn)
		self.log("files="+str(self.files))
		print(".")
		with zipfile.ZipFile("application.zip", "w") as zipf:
			for item in self.files:
				zipf.write(item)
				print("\rStoring `%s`                            "%item, end="")
		print("")
	
	def deploy(self):
		
		self.log("Building ZIP")
		self.build_zip()
		self.log("deploying...")
		for host, auth in self.servers.items():
			username, password=auth.split(":")
			self.log("Connecting to host=%s\t user=%s\t pass=%s" % (host, username, password))
			ssh=paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(host, username=username, password=password)
			r=str(ssh.exec_command("ls")[1].read())
			if self.taskname in r:
				self.log("Destroying old dir")
				waitfor(ssh.exec_command("rm -rf "+self.taskname))
			self.log("Starting SFTP session")
			sftp=ssh.open_sftp()
			self.log("Creating dir "+self.taskname)
			sftp.mkdir(self.taskname)
			self.log("Uploading...")
			sftp.put("application.zip", self.taskname+"/application.zip")
			self.log("Unzipping...")
			waitfor(ssh.exec_command("cd "+self.taskname+";unzip application.zip"))
			ssh.close()

	def get_sum_nproc(self):
		if not self.nproc:
			nproc=0
			self.nproc_count=collections.OrderedDict()
			for host, auth in self.servers.items():
				username, password=auth.split(":")
				# self.log("Connecting ip=%s\t user=%s\t pass=%s" % (host, username, password))
				ssh=paramiko.SSHClient()
				ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
				ssh.connect(host, username=username, password=password)
				server_nproc=int(waitfor(ssh.exec_command("nproc"))[1].read())
				self.nproc_count[host]=server_nproc
				nproc+=server_nproc
				ssh.close()
			self.nproc=nproc
		return self.nproc

	def start_workers(self, args):
		print("===STARTING WORKRERS===")
		self.connections={}
		self.channels={}
		self.channel_caches={}
		for host, auth in self.servers.items():
			username, password=auth.split(":")
			# self.log("Connecting ip=%s\t user=%s\t pass=%s" % (host, username, password))
			ssh=paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(host, username=username, password=password)
			chan=ssh.invoke_shell()
			# transport=ssh.get_transport()
			# chan=transport.open_session()
			# chan.get_pty()
			# chan.invoke_shell()
			self.connections[host]=ssh
			self.channels[host]=chan
			chan.set_combine_stderr(True)
			self.channel_caches[host]=""
			print((host,auth,args[self.server_order[host]]))
			cmd="cd "+self.taskname+";"+self.command.format(**args[self.server_order[host]])
			print("  ->  "+cmd)
			chan.send(cmd+"\n")

	def read_channels(self):
		lines=[]
		BUF_SIZE=2048
		# print("in read_channels")
		for host, chan in self.channels.items():
			lines.append([])
			# print(chan.recv_ready())
			while chan.recv_ready():
				r=chan.recv(BUF_SIZE).decode("utf-8")
				# print(r)
				self.channel_caches[host]+=r 

			if "\n" in self.channel_caches[host]:
				s=self.channel_caches[host].split("\n")
				lines[-1]=s[:-1]
				self.channel_caches[host]=s[-1]
		return lines

	# 	def start_workers(self, args):
	# 	print("===STARTING WORKRERS===")
	# 	self.connections={}
	# 	self.channels={}
	# 	self.channel_caches={}
	# 	for host, auth in self.servers.items():
	# 		username, password=auth.split(":")
	# 		# self.log("Connecting ip=%s\t user=%s\t pass=%s" % (host, username, password))
	# 		ssh=paramiko.SSHClient()
	# 		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	# 		ssh.connect(host, username=username, password=password)
	# 		transport=ssh.get_transport()
	# 		chan=transport.open_session()
	# 		self.connections[host]=ssh
	# 		self.channels[host]=chan
	# 		chan.set_combine_stderr(True)
	# 		self.channel_caches[host]=""
	# 		print((host,auth,args[self.server_order[host]]))
	# 		cmd="cd "+self.taskname+";"+self.command.format(**args[self.server_order[host]])
	# 		print("  ->  "+cmd)
	# 		chan.exec_command(cmd)

	# def read_channels(self):
	# 	lines=[]
	# 	BUF_SIZE=2048
	# 	print("in read_channels")
	# 	for host, chan in self.channels.items():
	# 		lines.append([])
	# 		print(chan.recv_ready())
	# 		while chan.recv_ready():
	# 			r=chan.recv(BUF_SIZE).decode("utf-8")
	# 			# print(r)
	# 			self.channel_caches[host]+=r 

	# 		if "\n" in self.channel_caches[host]:
	# 			s=self.channel_caches[host].split("\n")
	# 			lines[-1]=s[:-1]
	# 			self.channel_caches[host]=s[-1]
	# 	return lines


	def close_connections(self):
		[x.close() for x in self.connections.values()]

if __name__=="__main__":
	import pconfig
	if len(sys.argv)>1:
		if sys.argv[1]=="nproc":
			print("Cumulative processor count = "+str(pconfig.task.get_sum_nproc()))
		elif sys.argv[1]=="deploy":
			pconfig.task.deploy()
		else:
			print("No command.")
	else:
		print("No command.")