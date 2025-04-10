function add_notification(title, content, route){
  const date = new Date().toISOString();
  const formattedDate = date.toISOString().replace('T', ' ').replace('Z', '') + "+0000";
  body = {'seen': false, 'title': title, 'content': content, 'time': formattedDate, 'route': route};
  fetch('/save_notification', {method: 'POST', body: JSON.stringify(formattedDate)})
}