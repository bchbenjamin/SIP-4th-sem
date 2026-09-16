import os
import paramiko
from stat import S_ISDIR

def upload_dir(sftp, local_dir, remote_dir):
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass
        
    for item in os.listdir(local_dir):
        if item == '__pycache__':
            continue
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        
        if os.path.isfile(local_path):
            sftp.put(local_path, remote_path)
            print(f"Uploaded {local_path} -> {remote_path}")
        elif os.path.isdir(local_path):
            upload_dir(sftp, local_path, remote_path)

def main():
    host = '192.168.0.125'
    user = 'benjamin'
    pwd = '3318'
    
    transport = paramiko.Transport((host, 22))
    transport.connect(username=user, password=pwd)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # Upload train_autonomous.py
    sftp.put(r'c:\SIP-Prototype\Prototype\pi\train_autonomous.py', '/home/benjamin/edge-ai/train_autonomous.py')
    print("Uploaded train_autonomous.py")
    
    # Upload dataset
    upload_dir(sftp, r'c:\SIP-Prototype\Prototype\weapon-detection-1', '/home/benjamin/edge-ai/weapon-detection-1')
    print("Uploaded dataset")
    
    sftp.close()
    transport.close()

if __name__ == "__main__":
    main()
