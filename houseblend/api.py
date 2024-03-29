from flask import Blueprint, Response, request, send_from_directory, render_template
import os
import json
import glob
from datetime import datetime
import shutil

def create_bp(config):

    bp = Blueprint('api', __name__, url_prefix='/api')

    basedir = os.path.abspath(config['BASE_DIR'])
    renderdir = os.path.join(basedir, 'renders')
    os.makedirs(renderdir, exist_ok=True)

    jobs = []

    def find_job(job_id):
        for job in jobs:
            if job['id'] == job_id:
                return job
        raise KeyError("No such job")
    
    def write_job(job):
        filename = os.path.join(renderdir, job['id'], 'job.json')
        with open(filename, 'w') as f:
            json.dump(job, f)


    @bp.get('/config')
    def get_config():
        return {
            'basedir': basedir,
            'renderdir': renderdir,
        }

    # PROJECTS
    @bp.get('/projects')
    def get_projects():
        return [ os.path.basename(x)[:-6] for x in glob.glob(os.path.join(basedir, "*.blend")) ]
    
    # JOBS
    @bp.get('/jobs')
    def get_queued():
        return jobs
    
    @bp.put("/jobs")
    def add_job():
        try:
            data = request.get_json()
            project = data['project']
            start_frame = int(data['start'])
            end_frame = int(data['end'])
            priority = int(data.get('priority', 0))
        except:
            return Response("Malformed input", 400)

        job = {
            'id': datetime.now().isoformat(timespec='microseconds'),
            'project': project,
            'start': start_frame,
            'end': end_frame, 
            'priority': priority,
            'queued': list(range(start_frame, end_frame+1)),
            'total': end_frame - start_frame + 1,
            'status': 'accepted',
            'assigned': {},
            'complete': {},
        }
        projectdir = os.path.join(renderdir, job['id'])
        os.makedirs(projectdir, exist_ok=True)
        write_job(job)

        shutil.copy(f"{project}.blend", f"{projectdir}/{project}.blend")

        jobs.append(job)
        jobs.sort(key=lambda x: (x['priority'], x['id']))
        return Response(json.dumps(job), 201, mimetype="application/json")

    @bp.delete("/jobs/<jobid>")
    def delete_job(jobid):
        try:
            job = find_job(jobid)
            jobs.remove(job)
            return Response('Job deleted', 204)
        except KeyError:
            return Response('No such job', 404)

    # RENDERS
    @bp.get("/renders")
    def get_renders():
        result = os.listdir(renderdir)
        result.sort(reverse=True)
        return result

    @bp.get('/renders/<jobid>')
    def job_file_list(jobid):
        try:
            job = find_job(jobid)
        except KeyError:
            return Response('No such job', 404)
        return glob.glob(os.path.join(renderdir, job['id']), "*.png")

    @bp.get("/renders/<jobid>/<path:filename>")
    def download_render(jobid, filename):
        folder = os.path.join(renderdir, jobid) 
        return send_from_directory(folder, filename)

    @bp.put("/renders/<jobid>/<path:filename>")
    def upload_render(jobid, filename):
        try:
            job = find_job(jobid)
        except KeyError:
            return Response('No such job', 404)
        upload_dir = os.path.join(renderdir, job['id'])
        fn = os.path.join(upload_dir, filename)
        with open(fn, 'wb') as f:
            f.write(request.data)
        return Response('File uploaded', 201)
        

    # TASKS    
    @bp.get('/tasks/request')
    def request_task():
        frames = int(request.args.get('frames', 1))

        for job in jobs:
            if len(job['queued']) == 0:
                continue
            
            job['status'] = 'processing'
            task = {
                'job_id': job['id'],
                'project': job['project'],
                'frames': job['queued'][:frames],
                'worker': request.remote_addr,
                'time': datetime.now().isoformat(timespec="seconds")
            }
            task_id = f"{task['frames'][0]}_{task['frames'][-1]}"
            task['task_id'] = task_id
            job['queued'] = job['queued'][frames:]
            job['assigned'][task_id] = task
            return task
        
        return Response('No jobs available', 204)

    @bp.put('/tasks/complete')
    def task_completed():
        data = request.get_json()
        job = find_job(data['job_id'])
        task = job['assigned'].pop(data['task_id'])

        started = datetime.fromisoformat(task['time'])
        task['duration'] = (datetime.now() - started).seconds
        task['status'] = 'complete'

        job['complete'][task['task_id']] = task

        if not job['queued'] and not job['assigned']:
            job['status'] = "complete"
            write_job(job)
            jobs.remove(job)

        return Response('Task marked complete', 201)

    @bp.put('/tasks/failed')
    def task_failed():
        data = request.get_json()
        job = find_job(data['job_id'])
        task = job['assigned'].pop(data['task_id'])
        
        # TODO: store failed tasks?
        
        job['queued'].extend(task['frames'])
        return Response('Task requeued', 201)
    
    return bp
    