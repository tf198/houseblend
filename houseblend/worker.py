from uuid import uuid4
import requests
import time
import tempfile
import os.path
import subprocess
import json

import logging
logger = logging.getLogger(__name__)

def handle_task(task):
    logger.info(task)
    frames = ','.join([ str(x) for x in task['frames'] ])
    cmd = [task['blender'], '-b', task['blendfile'],
           '-o', f'{task["workdir"]}/output-#####.png',
           '-f', frames,
           ]
    logger.debug(cmd)
    subprocess.run(cmd, check=True)
    results = [f"{task['workdir']}/output-{i:05d}.png" for i in task['frames'] ]
    for result in results:
        if not os.path.isfile(result):
            raise RuntimeError(f"Failed to render {result}")
    return results


def run_worker(manager, frames, blender):
    
    uid = str(uuid4())
    logger.info("Worker UUID: %s", uid)

    logger.info("Registering worker with %s", manager)

    def send(uri, data):
        body = json.dumps(data)
        r = requests.put(f'http://{manager}/{uri}', data=body, headers={'Content-Type': 'application/json'})
        if r.status_code not in [200, 201, 204]:
            logger.warning(r.text)
            raise RuntimeError(f"Failed to upload data to {uri}")
        
    def send_file(uri, filename):
        with open(filename, 'rb') as f:
            r = requests.put(f'http://{manager}/{uri}', data=f)
            if r.status_code not in [200, 201, 204]:
                logger.warning(r.text)
                raise RuntimeError(f"Failed to upload file: {filename} to {uri}")

    with tempfile.TemporaryDirectory() as workdir:

        while True:
            r = requests.get(f'http://{manager}/tasks/request?frames={frames}')
            
            if r.status_code != 200:
                logger.debug("No tasks - waiting")
                time.sleep(5)
                continue

            task = r.json()
            logger.info(task)

            jobdir = os.path.join(workdir, task['job_id'])
            os.makedirs(jobdir, exist_ok=True)

            blendfile = os.path.join(jobdir, f'{task['project']}.blend')
            if not os.path.isfile(blendfile):
                logger.info("Requesting project file")
                r = requests.get(f'http://{manager}/projects/{task['project']}')
                with open(blendfile, 'wb') as f:
                    f.write(r.content)
            task['blendfile'] = blendfile
            task['workdir'] = jobdir
            task['blender'] = blender

            try:
                images = handle_task(task)

                for i in images:
                    n = os.path.basename(i)
                    send_file(f"renders/{task['job_id']}/{n}", i)

                send('tasks/complete', task)
            except Exception as e:
                task['error'] = str(e)
                send('tasks/failed', task)
                raise
            time.sleep(2)


if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser("HouseBlend")

    parser.add_argument('--blender', '-b', default='blender', help='Blender executable')
    parser.add_argument('--frames', '-f', type=int, default=1, help='Frames to render per task')

    parser.add_argument('--loglevel', '-l', default='info', help='Logging level')
    parser.add_argument('manager', nargs="?", default="localhost:5000", help='Manager to connect to')

    options = parser.parse_args()

    logging.basicConfig(level=getattr(logging, options.loglevel.upper(), logging.INFO))

    kwargs = vars(options)
    for i in ('loglevel', ):
        kwargs.pop(i)

    logger.debug(options)
    run_worker(**kwargs)