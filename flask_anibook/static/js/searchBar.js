/* handle the behaviour, animation and some appearance of the search bar */

const url_path = window.location.href
var url_object = new URL(url_path)

function searchBarDefaultSelection(url_object) {
  var path = url_object.pathname
  var select_object = document.getElementsByClassName('search-bar-list-option')
  var selected = false
  for (let x = 0; x < select_object.length; x++) {
    var optionInnerHtml = select_object[x].innerHTML.replace(/\s+/g, '')
    if (`/${optionInnerHtml}` == path) {
      select_object[x].setAttribute('selected', 'selected')
    }
  }
  if (!selected) {
    console.log('did not select anime list')
  }
}

searchBarDefaultSelection(url_object)
