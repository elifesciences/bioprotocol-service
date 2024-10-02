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
