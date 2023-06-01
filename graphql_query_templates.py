from string import Template

add_comment_template = Template("""
addComment(input: { subjectId: "$issue_id", body: "$comment_body" }) {
  commentEdge {
    node {
      id
      body
    }
  }
}
""")

create_issue_template = Template("""
createIssue(input: { repositoryId: "$repo_id", title: "$title", body: "$body" }) {
  issue {
    id
    number
  }
}
""")

find_repo_id_template = Template("""
repository(owner: "$owner", name: "$repo") {
  id
}
""")

main_query_template = Template("""
search(
  first: 100
  query: "repo:$repo is:issue updated:>=$timestamp"
  type: ISSUE
  after: $cursor
) {
  pageInfo {
    endCursor
    hasNextPage
  }
  nodes {
    ... on Issue {
      title
      id
      url
      number
      body
      createdAt
      author {
        login
      }
      lastEditedAt
      editor {
        login
      }
  
      comments(first: 100) {
        pageInfo {
          endCursor
          hasNextPage
        }
        nodes {
          author {
            login
          }
          url
          createdAt
          lastEditedAt
          body
          editor {
            login
          }
        }
      }
    }
  }
}
""")

read_comments_template = Template("""
resource(url: "$url") {
    ... on Issue {
        comments(first:100, after: "$cursor") {
            pageInfo {
                endCursor
                hasNextPage
            }
            nodes{
                author {
                    login
                }
                url
                createdAt
                lastEditedAt
                body
                editor {
                    login
                }
            }
        }
    }
}
""")

read_last_comment_template = Template("""
node(id: "$issue_id") {
  ... on Issue {
    comments(last: 1) {
      nodes {
        createdAt
      }
    } 
  }
}
""")

update_issue_template = Template("""
updateIssue(input: {id: "$issue_id", body: "$issue_body"}) {
    issue {
        id
    }
}
""")
