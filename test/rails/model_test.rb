require File.dirname(__FILE__) + "/rails_test_helper.rb"

describe MyModel, :type => ActiveSupport::TestCase do
  before do
    @my_model = MyModel.create!
  end
  
  it "is my model" do
    @my_model.should be(@my_model)
  end
  
  it "has a title" do
    @my_model.title = "Title"
    @my_model.save!
    @my_model.title.should eql("Title")
  end
end

