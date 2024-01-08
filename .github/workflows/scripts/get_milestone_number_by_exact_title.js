module.exports = (async function ({github, context}) {
    const milestone_title = process.env.MILESTONE_TITLE;
    const [repo_owner, repo_name] = process.env.GITHUB_REPOSITORY.split('/');

    const {
        repository: {
            milestones: {
                nodes: milestones,
                pageInfo: {hasNextPage}
            }
        }
    } = await github.graphql({
        query: `
        query getMilestoneNumberByTitle(
          $repo_owner: String!
          $repo_name: String!
          $milestone_title: String!
        ) { 
          repository(owner:$repo_owner name:$repo_name) {
            milestones(query:$milestone_title states:OPEN first:100) {
              nodes {
                number
                title
              }
              pageInfo {
                hasNextPage
              }
            }
          }
        }`,
        repo_owner: repo_owner,
        repo_name: repo_name,
        milestone_title: milestone_title,
    });

    if (hasNextPage) {
        // this should realistically never happen so let's just error
        core.setFailed('Impossible happened! :)');
        return;
    }

    for (const milestone of milestones)
        if (milestone.title === milestone_title)
            return milestone.number;

    // if no exact match is found, assume the milestone doesn't exist
    console.log('The milestone was not found. API returned the array: %o', milestones);
    return null;
})
