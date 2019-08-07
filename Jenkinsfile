elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }
 
    stage 'Project tests', {
        lock('bioprotocol--ci') {
            builderDeployRevision 'bioprotocol--ci', commit
            builderProjectTests 'bioprotocol--ci', '/srv/bioprotocol'
        }
    }
    
    elifeMainlineOnly {
        stage 'End2end tests', {
            builderDeployRevision 'bioprotocol--end2end', commit
            //TODO: no end2end test cover the integration with this service yet?
            //elifeSpectrum(
            //    deploy: [
            //        stackname: 'bioprotocol--end2end',
            //        revision: commit,
            //        folder: '/srv/bioprotocol'
            //    ],
            //    marker: 'bioprotocol'
            //)
        }

        //stage 'Deploy on staging', {
        //    lock('bioprotocol--staging') {
        //        builderDeployRevision 'bioprotocol--staging', commit
        //        builderSmokeTests 'bioprotocol--staging', '/srv/bioprotocol'
        //    }
        //}
     
        stage 'Approval', {
            elifeGitMoveToBranch commit, 'approved'
        }
    }
}
