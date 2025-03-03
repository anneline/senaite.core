import React from "react";


class SelectedValues extends React.Component {

  constructor(props) {
    super(props);

    this.on_change = this.on_change.bind(this);
    this.on_deselect = this.on_deselect.bind(this);
  }

  get_selected_values() {
    return this.props.values || [];
  }

  /*
   * Simple template interpolation that replaces ${...} placeholders
   * with any found value from the context object.
   *
   * https://stackoverflow.com/questions/29182244/convert-a-string-to-a-template-string
   */
  interpolate(template, context) {
    for(let [key, value] of Object.entries(context)) {
      template = template.replace(new RegExp('\\$\\{' + key + '\\}', 'g'), value)
    }
    return template;
  }

  render_display_template(value) {
    let template = this.props.display_template;
    if (!template) return value;
    let context = this.props.records[value];
    if (!context) return value;
    return this.interpolate(template, context);
  }

  build_selected_items() {
    let items = [];
    let selected_values = this.get_selected_values();

    for (let value of selected_values) {
      items.push(
        <li value={value} className="d-inline-block">
          <div className="p-1 mb-1 mr-1 bg-light border rounded field-validation">
            <span dangerouslySetInnerHTML={{__html: this.render_display_template(value)}}></span>
            <button value={value}
                    className="btn btn-sm btn-link-danger"
                    onClick={this.on_deselect}>
              <i className="fas fa-times-circle"></i>
            </button>
          </div>

        </li>
      );
    }
    return items
  }

  /*
   * Callback when the textarea field was changed
   * Note: This will be useful when the field is used in the sample add form
   */
  on_change(event) {
    event.preventDefault();
    let target = event.currentTarget;
    let value = target.value;
    let values = value.split("\n");
    // filter out empties
    values = values.filter(x => x);
    // set new values directly
    if (this.props.set_values) {
      this.props.set_values(values);
    }
  }

  on_deselect(event) {
    event.preventDefault();
    let target = event.currentTarget;
    let value = target.getAttribute("value");
    console.debug("SelectedValues::on_deselect: Remove value", value);
    if (this.props.on_deselect) {
      this.props.on_deselect(value);
    }
  }

  render() {
    return (
      <div className="queryselectwidget-selected-values">
        <ul className="list-unstyled d-table-row">
          {this.build_selected_items()}
        </ul>
        {/* submitted in form */}
        <textarea
          className="d-none"
          onChange={this.on_change}
          name={this.props.name}
          value={this.props.values.join("\n")}
        />
      </div>
    );
  }
}

export default SelectedValues;
