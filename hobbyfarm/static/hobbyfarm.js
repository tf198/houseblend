
function prettyDate(d) {
    return d.substring(0, 10) + " " + d.substring(11,19)
}

function hobbyfarm() {
    return {
        projects: [],
        jobs: [],
        renders: [],
        selectedJob: null,
        selectedRender: null,
        previewUrl: "",

        async retrieve(url) {
            //console.log("Fetching " + url)
            const response = await fetch(url);
            if (response.status != 200) {
                message = await response.text();
                alert(response.status + ": " + message);
                throw (message);
            }
            return await response.json();
        },

        async createJob(project) {
            const frames = prompt("Enter frames [a:b]");
            if (!frames) return;
            const parts = frames.split(':');
            const data = {
                project: project,
                start: parseInt(parts[0]),
                end: parseInt(parts[1]),
            }
            console.log("Creating job:", data);
            const response = await fetch('/jobs', {
                method: 'PUT',
                body: JSON.stringify(data),
                headers: { 'Content-type': 'application/json; charset=UTF-8' }
            })
            if (response.status != 201) {
                message = await response.text();
                alert(response.status + ": " + message);
                throw (message);
            }
            this.fetchJobs();
        },

        async deleteJob(id) {
            console.log("Deleting job:", id);
            const response = await fetch('/jobs/' + id, {
                method: 'DELETE'
            });
            console.log(response);
            this.fetchJobs();
        },

        async fetchJobs() {
            this.jobs = await this.retrieve('/jobs');
            // update the currently selected job
            if (this.selectedJob) {
                for(job of this.jobs) {
                    if (job.id == this.selectedJob.id) {
                        this.selectedJob=job;
                        return;
                    }
                }
            }
        },

        async fetchProjects() {
            this.projects = await this.retrieve('/projects');
        },

        async fetchRenders() {
            this.renders = await this.retrieve('/renders');
        },

        async viewRender(render) {
            this.selectedRender = render;
            this.previewUrl = "";
            this.selectedJob = await this.retrieve('/renders/' + render + "/job.json");
        },

        async viewJob(job) {
            this.selectedJob = job;
            this.selectedRender = null;
            this.previewUrl = "";
        },

        init() {
            console.log('init');
            this.fetchProjects();
            this.fetchJobs();
            this.fetchRenders();
            setInterval(() => this.fetchJobs(), 5000)
        }
    }
}