require File.dirname(__FILE__) + "/rails_test_helper.rb"

describe MyModel, :type => ActiveSupport::TestCase do
  before do
    @my_model = MyModel.create!
  end
  
  it "is my model" do
    @my_model.should be(@my_model)
  end
end

