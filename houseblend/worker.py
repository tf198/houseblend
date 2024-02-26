from uuid import uuid4
import requests
import time
import tempfile
import os.path
import subprocess
import json

import logging
logger = logging.getLogger(__name__)

class API(object):

    def __init__(self, baseurl):
        self.baseurl = baseurl

    def send(self, uri, data):
        body = json.dumps(data)
        r = requests.put(f'{self.baseurl}/{uri}', data=body, headers={'Content-Type': 'application/json'})
        if r.status_code not in [200, 201, 204]:
            logger.warning(r.text)
            raise RuntimeError(f"Failed to upload data to {uri}")
        
    def send_file(self, uri, filename):
        with open(filename, 'rb') as f:
            r = requests.put(f'{self.baseurl}/{uri}', data=f)
            if r.status_code not in [200, 201, 204]:
                logger.warning(r.text)
                raise RuntimeError(f"Failed to upload file: {filename} to {uri}")
            
    def get_file(self, uri, f):
        r = requests.get(f'{self.baseurl}/{uri}')
        if r.status_code != 200:
            logger.warning(r.text)
            raise RuntimeError("Failed to download file")
        f.write(r.content)


def handle_render_task(task, api):
    logger.debug("handle_render_task: %r", task)
    
    # get the blendfile (if we dont already have it)
    blendfile = os.path.join(task['workdir'], f"{task['project']}.blend")
    if not os.path.isfile(blendfile):
        logger.info("Requesting project file")
        with open(blendfile, 'wb') as f:
            api.get_file(f"renders/{task['job_id']}/{task['project']}.blend", f)
    
    
    # spawn a blender process
    frames = ','.join([ str(x) for x in task['frames'] ])
    cmd = [task['blender'], '-b', blendfile,
           '-o', f"{task['workdir']}/output-#####.png",
           '-f', frames,
           ]
    logger.debug(cmd)
    subprocess.run(cmd, check=True)

    # upload the results
    logger.info("Uploading frames %r", task['frames'])
    for i in task['frames']:
        framename = f'output-{i:05d}.png'
        filename = os.path.join(task['workdir'], framename)
        if not os.path.isfile(filename):
            raise RuntimeError(f"Failed to render frame {i}")
        api.send_file(f"renders/{task['job_id']}/{framename}", filename)




def run_worker(manager, port, frames, blender):
    
    uid = str(uuid4())
    logger.info("Worker UUID: %s", uid)

    logger.info("Checking blender...")
    subprocess.run([blender, '--version'], check=True)

    logger.info("Registering worker with %s", manager)
    api = API(f'http://{manager}:{port}/api')


    with tempfile.TemporaryDirectory() as workdir:

        while True:
            r = requests.get(f'http://{manager}:{port}/api/tasks/request?frames={frames}') # TODO: switch to API
            
            if r.status_code != 200:
                logger.debug("No tasks - waiting")
                time.sleep(5)
                continue

            task = r.json()
            logger.info("Received task: %r", task['job_id'])

            jobdir = os.path.join(workdir, task['job_id'])
            os.makedirs(jobdir, exist_ok=True)
            task['workdir'] = jobdir
            task['blender'] = blender

            try:
                handle_render_task(task, api)
                api.send('tasks/complete', task)
            except Exception as e:
                task['error'] = str(e)
                api.send('tasks/failed', task)
                raise # something wrong - don't keep trying
            
            logger.info("Completed task %s, waiting for next..", task['job_id'])


def main():
    import argparse

    parser = argparse.ArgumentParser("HouseBlend")

    parser.add_argument('--blender', '-b', default='blender', help='Blender executable')
    parser.add_argument('--frames', '-f', type=int, default=1, help='Frames to render per task')

    parser.add_argument('--loglevel', '-l', default='info', help='Logging level')
    parser.add_argument('--port', type=int, default=5000, help="Manager port")
    parser.add_argument('manager', nargs="?", default="localhost", help='Manager to connect to')

    options = parser.parse_args()

    logging.basicConfig(level=getattr(logging, options.loglevel.upper(), logging.INFO))

    kwargs = vars(options)
    for i in ('loglevel', ):
        kwargs.pop(i)

    logger.debug(options)
    run_worker(**kwargs)

if __name__ == '__main__':
    main()