# Linear

Use Symphony's `linear_graphql` client tool for Linear operations.

## Query Issue

```graphql
query {
  issue(identifier: "WEA-123") {
    id title description state { name } labels { nodes { name } }
  }
}
```

## Update State

```graphql
mutation {
  issueUpdate(id: "issue-id", input: { stateId: "new-state-id" }) {
    success issue { id state { name } }
  }
}
```

## Add Comment

```graphql
mutation {
  commentCreate(input: { issueId: "issue-id", body: "text" }) {
    success comment { id }
  }
}
```

## Required States

- Todo, In Progress, Human Review, Merging, Rework, Done
